from celery import shared_task
from celery.task import periodic_task
from datetime import timedelta
import pytz
from django.utils import timezone
from django.db.models import Q

from twdata import userdata
from .models import User, Relo, CeleryTask

from .methods import kill_celery_task, check_spam_account, add_user, create_relo, save_tweet, update_tracked_tags
from .config import REQUIRED_IN_DEGREE, REQUIRED_OUT_DEGREE

#Uncomment the decorators here to allow tasks to run periodically. Requires a running Celery Beat (see Readme)
#@periodic_task(run_every=timedelta(hours=24), bind=True)
def update_user_relos_periodic(self):
    update_user_relos_task()
    return
#@periodic_task(run_every=timedelta(hours=6), bind=True)
def trim_spam_accounts_periodic(self):
    trim_spam_accounts()
    return
#@periodic_task(run_every=timedelta(minutes=30), bind=True)
def update_data_periodic(self):
    update_tracked_tags()
    add_users_from_mentions()
    return


@shared_task(bind=True)
def trim_spam_accounts(self):
    # Remove existing task and save new task to DB
    kill_celery_task('trim_spam_accounts')
    task_object = CeleryTask(celery_task_id=self.request.id, task_name='trim_spam_accounts')
    task_object.save()

    # Get unsorted users (alters with user_class = 0) with the requisite in/out degree
    users = User.objects.filter(user_class=0).filter(screen_name__isnull=True).filter(Q(in_degree__gte=REQUIRED_IN_DEGREE) | Q(out_degree__gte=REQUIRED_OUT_DEGREE))

    length = users.count()
    print("length of class 0 users to sort: {}".format(length))

    #Requesting User objects in batches to minimise API limits
    while length > 0:
        if length > 99:
            end = 100
        else:
            end = length
        chunk = users[0:end]
        #process chunk
        user_ids = chunk.values_list('user_id', flat=True)
        user_list = userdata.lookup_users(user_ids=user_ids)

        for user_data in user_list:
            u = users.get(user_id=int(user_data.id_str))
            #Class the user as spam or 'alter'
            if check_spam_account(user_data):
                u.user_class = -1
            else:
                u.user_class = 1
            #If timezone is an issue:
            try:
                tz_aware = timezone.make_aware(user_data.created_at, timezone.get_current_timezone())
            except pytz.exceptions.AmbiguousTimeError:
                # Adding an hour to avoid DST ambiguity errors.
                time_adjusted = user_data.created_at + timedelta(minutes=60)
                tz_aware = timezone.make_aware(time_adjusted, timezone.get_current_timezone())
            #TODO: Need all these? Perhaps only for user_class >0? Merge with add_user section?
            u.created_at = tz_aware
            u.followers_count = user_data.followers_count
            u.friends_count = user_data.friends_count
            u.geo_enabled = user_data.geo_enabled
            u.location = user_data.location
            u.name = user_data.name
            u.screen_name = user_data.screen_name
            u.statuses_count = user_data.statuses_count
            u.save()
        length -= 100

    CeleryTask.objects.get(celery_task_id=self.request.id).delete()
    return


@shared_task(bind=True)
def save_twitter_object_task(self, tweet=None, user_class=0, save_entities=False, **kwargs):
    #Save task to DB
    task_object = CeleryTask(celery_task_id = self.request.id, task_name='save_twitter_object')
    task_object.save()

    try:
        user_data = userdata.get_user(**kwargs)
        add_user(user_class=user_class, user_data=user_data)
    except:
        print('Error adding user.')
        pass

    if tweet:
        save_tweet(tweet, save_entities)

    CeleryTask.objects.get(celery_task_id=self.request.id).delete()
    return


#TODO: Move to methods and import?
#TODO: Currently appears buggy. Lists too long shortly after adding user, should be near-0
@shared_task(bind=True)
def update_user_relos_task(self):
    # Remove existing task and save new task to DB
    kill_celery_task('update_user_relos')
    task_object = CeleryTask(celery_task_id = self.request.id, task_name='update_user_relos')
    task_object.save()

    users = User.objects.filter(user_class__gte=2)
    print('Updating relo information for {} users.'.format(len(users)))

    for user in users:
        #TODO: Possible add check: is new/dead links are over threshold, mark account as spam.
        # Particularly dead links, as new links may signify virality

        #Get true list of users followed by account
        user_following=userdata.friends_ids(user_id=user.user_id)
        if not user_following:
            #TODO: Handle suspended/deleted user here
            continue
        #Get recorded list of users followed by account
        user_following_recorded = list(Relo.objects.filter(sourceuser=user).filter(end_observed_at=None).values_list('targetuser__user_id', flat=True))

        new_friend_links = [a for a in user_following if (a not in user_following_recorded)]
        dead_friend_links = [a for a in user_following_recorded if (a not in user_following)]

        if len(new_friend_links):
            #print("New friend links for user: {}: {}".format(user.screen_name, new_friend_links))
            print("{} new friend links for user: {}".format(len(new_friend_links), user.screen_name))
        if len(dead_friend_links):
            #print("Dead friend links for user: {}: {}".format(user.screen_name, dead_friend_links))
            print("{} dead friend links for user: {}".format(len(dead_friend_links), user.screen_name))

        for target_user_id in dead_friend_links:
            for ob in Relo.objects.filter(sourceuser=user, targetuser__user_id__contains=target_user_id).filter(end_observed_at=None):
                ob.end_observed_at = timezone.now()
                ob.save()
            tuser = User.objects.get(user_id=target_user_id)
            tuser.in_degree = tuser.in_degree - 1
            tuser.save()

            #Commented out to reduce DB calls:
            #user.out_degree -= 1
            #user.save()
        for targetuser in new_friend_links:
            create_relo(user, targetuser, outgoing=True)

        #Get true list of users following an account
        user_followers = userdata.followers_ids(user_id=user.user_id)
        if not user_followers:
            #TODO: Handle suspended/deleted user here
            continue
        #Get recorded list of users following an account
        user_followers_recorded = list(Relo.objects.filter(targetuser=user).filter(end_observed_at=None).values_list('sourceuser__user_id', flat=True))

        new_follower_links = [a for a in user_followers if (a not in user_followers_recorded)]
        dead_follower_links = [a for a in user_followers_recorded if (a not in user_followers)]

        if len(new_follower_links):
            #print("New follower links for user: {}: {}".format(user.screen_name, new_follower_links))
            print("{} new follower links for user: {}".format(len(new_follower_links), user.screen_name))
        if len(dead_follower_links):
            #print("Dead follower links for user: {}: {}".format(user.screen_name, dead_follower_links))
            print("{} dead follower links for user: {}".format(len(dead_follower_links), user.screen_name))

        for source_user_id in dead_follower_links:
            for ob in Relo.objects.filter(targetuser=user, sourceuser__user_id__contains=source_user_id).filter(end_observed_at=None):
                ob.end_observed_at = timezone.now()
                ob.save()
            suser = User.objects.get(user_id=source_user_id)
            suser.in_degree = suser.in_degree - 1
            suser.save()

            #Commented out to reduce DB calls:
            #user.in_degree -= 1
            #user.save()
        for source_user in new_follower_links:
            create_relo(user, source_user, outgoing=False)

    print('Updating relo information complere')

    CeleryTask.objects.get(celery_task_id=self.request.id).delete()
    return
