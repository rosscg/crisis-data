from celery import shared_task
from celery.task import periodic_task

from twdata import userdata
from .models import User, Relo, CeleryTask

#Not used:
from dateutil.parser import parse
#from pytz import timezone

from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta

from django.db.models import Q

from .methods import kill_celery_task, check_spam_account
from .config import REQUIRED_IN_DEGREE, REQUIRED_OUT_DEGREE

#TODO: Replace into target method.
#@periodic_task(run_every=timedelta(minutes=10), bind=True)
def update_user_relos_periodic(self):
    update_user_relos_task()
    return
#@periodic_task(run_every=timedelta(minutes=10), bind=True)
def trim_spam_accounts_periodic(self):
    trim_spam_accounts()
    return

#TODO: Set as periodic? Add revoke and db record as in update_user_relos_task
@shared_task(bind=True)
def trim_spam_accounts(self):
    # Remove existing task
    kill_celery_task('trim_spam_accounts')
    print("Running trim_spam_accounts with id: {}".format(self.request.id))
    #Save task details to DB
    task_object = CeleryTask(celery_task_id = self.request.id, task_name='trim_spam_accounts')
    CeleryTask.objects.filter(celery_task_id=self.request.id).delete()
    task_object.save()

    # Get unsorted users (alters with user_class = 0) with the requisite in/out degree
    users = User.objects.filter(user_class=0).filter(screen_name__isnull=True).filter(Q(in_degree__gte=REQUIRED_IN_DEGREE) | Q(out_degree__gte=REQUIRED_OUT_DEGREE))

    length = users.count()
    print("length of class 0 users to sort: {}".format(length))

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
            if check_spam_account(user_data):
                u.user_class = -1
            else:
                u.user_class = 1
            #TODO: Need all these? Perhaps only for user_class >0? Merge with add_user section
            #If timezone is an issue:
            tz_aware = timezone.make_aware(user_data.created_at, timezone.get_current_timezone())
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
def add_user_task(self, user_class=0, **kwargs):

    task_object = CeleryTask(celery_task_id = self.request.id, task_name='add_user')
    task_object.save()

    user_data = userdata.get_user(**kwargs)
    add_user(user_class=user_class, user_data=user_data)

    CeleryTask.objects.get(celery_task_id=self.request.id).delete()
    return


def add_user(user_class=0, user_data=None, **kwargs):

    #TODO: Needs to check something other than username
    #User exists as a full user (ego)
    if 'screen_name' in kwargs:
        if User.objects.filter(screen_name=screen_name).exists():
            if User.objects.get(screen_name=screen_name).user_class >= 2:
                print("User {} already exists.".format(screen_name))
                return
    #Get user_data if not supplied
    if not user_data:
        user_data=userdata.get_user(**kwargs)
    if 'screen_name' not in kwargs:
        if User.objects.filter(screen_name=user_data.screen_name).exists():
            if User.objects.get(screen_name=user_data.screen_name).user_class >= 2:
                print("User {} already exists.".format(user_data.screen_name))
                return

    if check_spam_account(user_data):
        return

    #If user is an existing node_id (alter)
    if User.objects.filter(user_id=int(user_data.id_str)).exists():
        print("Updating record...")
        #u = User.objects.filter(user_id=int(userdict.get('id_str')))
        u = get_object_or_404(User, user_id=int(user_data.id_str))
        # Update added_at, as user is upgraded from alter to ego
        u.added_at = timezone.now()

    #User is a new observation
    else:
        #Creating user object
        print("Creating record...")
        u = User()

    #If timezone is an issue:
    tz_aware = timezone.make_aware(user_data.created_at, timezone.get_current_timezone())
    u.created_at = tz_aware

    u.default_profile = user_data.default_profile
    u.default_profile_image = user_data.default_profile_image
    u.description = user_data.description
    # u.entities = NOT IMPLEMENTED
    u.favourites_count = user_data.favourites_count
    u.followers_count = user_data.followers_count
    u.friends_count = user_data.friends_count
    u.geo_enabled = user_data.geo_enabled
    u.has_extended_profile = user_data.has_extended_profile
    u.is_translation_enabled = user_data.is_translation_enabled
    u.lang = user_data.lang
    u.listed_count = user_data.listed_count
    u.location = user_data.location
    u.name = user_data.name
    #u.needs_phone_verification = user_data.needs_phone_verification
    u.profile_background_color = user_data.profile_background_color
    u.profile_background_image_url = user_data.profile_background_image_url
    u.profile_background_image_url_https = user_data.profile_background_image_url_https
    u.profile_background_tile = user_data.profile_background_tile
    u.profile_image_url = user_data.profile_image_url
    u.profile_image_url_https = user_data.profile_image_url_https
    u.profile_link_color = user_data.profile_link_color
    #u.profile_location = user_data.profile_location
    u.profile_sidebar_border_color = user_data.profile_sidebar_border_color
    u.profile_sidebar_fill_color = user_data.profile_sidebar_fill_color
    u.profile_text_color = user_data.profile_text_color
    u.profile_use_background_image = user_data.profile_use_background_image
    u.protected = user_data.protected
    u.screen_name = user_data.screen_name
    u.statuses_count = user_data.statuses_count
    #u.suspended = user_data.suspended
    u.time_zone = user_data.time_zone
    u.translator_type = user_data.translator_type
    u.url = user_data.url
    u.user_id = int(user_data.id_str)
    u.utc_offset = user_data.utc_offset
    u.verified = user_data.verified

    u.user_class = user_class

    u.save()

    if user_class >= 2:
        #Get users followed by account & create relationship objects
        userfollowing = userdata.friends_ids(screen_name=user_data.screen_name)
        for targetuser in userfollowing:
            create_relo(u, targetuser, outgoing=True)

        #Get followers & create relationship objects
        userfollowers = userdata.followers_ids(screen_name=user_data.screen_name)
        print('Length of follower list: {}'.format(len(userfollowers)))
        for sourceuser in userfollowers:
            create_relo(u, sourceuser, outgoing=False)
    return u


#TODO: add user_followed_by functionality
@shared_task(bind=True)
def update_user_relos_task(self):
    # Remove existing task
    kill_celery_task('update_user_relos')
    print("Running update_user_relos_task with id: {}".format(self.request.id))
    #Save task details to DB
    task_object = CeleryTask(celery_task_id = self.request.id, task_name='update_user_relos')
    task_object.save()

    users = User.objects.filter(user_class__gte=2)

    for user in users:
        #Get users followed by account
        user_following = userdata.friends_ids(screen_name=user.screen_name)

        #Get recorded list of users followed by account
        #TODO: Filter out dead relos, but how to handle when recreated?
        user_following_recorded = list(Relo.objects.filter(sourceuser=user).filter(end_observed_at=None).values_list('targetuser', flat=True))

        new_friend_links = [a for a in user_following if (a not in user_following_recorded)]
        dead_friend_links = [a for a in user_following_recorded if (a not in user_following)]

        print("New friend links for user: {}: {}".format(user.screen_name, new_friend_links))
        print("Dead friend links for user: {}: {}".format(user.screen_name, dead_friend_links))

        for target_user_id in dead_friend_links:
            for ob in Relo.objects.filter(sourceuser=user, targetuser__user_id__contains=target_user_id).filter(end_observed_at=None):
                ob.end_observed_at = timezone.now()
                ob.save()
            tuser = User.objects.get(user_id=target_user_id)
            tuser.in_degree = tuser.in_degree - 1
            tuser.save()

            user.out_degree -= 1
            user.save()

        for targetuser in new_friend_links:
            create_relo(user, targetuser, outgoing=True)

        #Get users following an account
        user_followers = userdata.followers_ids(screen_name = user.screen_name)

        #Get recorded list of users following an account
        #TODO: Filter out dead relos, but how to handle when recreated?
        user_followers_recorded = list(Relo.objects.filter(targetuser=user).filter(end_observed_at=None).values_list('sourceuser', flat=True))

        new_follower_links = [a for a in user_followers if (a not in user_followers_recorded)]
        dead_follower_links = [a for a in user_followers_recorded if (a not in user_followers)]

        print("New follower links for user: {}: {}".format(user.screen_name, new_follower_links))
        print("Dead follower links for user: {}: {}".format(user.screen_name, dead_follower_links))

        for source_user_id in dead_follower_links:
            for ob in Relo.objects.filter(targetuser=user, sourceuser__user_id__contains=source_user_id).filter(end_observed_at=None):
                ob.end_observed_at = timezone.now()
                ob.save()
            suser = User.objects.get(user_id=source_user_id)
            suser.in_degree = suser.in_degree - 1
            suser.save()

            user.in_degree -= 1
            user.save()

        for source_user in new_follower_links:
            create_relo(user, source_user, outgoing=False)

    CeleryTask.objects.get(celery_task_id=self.request.id).delete()
    return

#TODO: move this elsewhere and import?
def create_relo(existing_user, new_user_id, outgoing):

    if outgoing:
        if Relo.objects.filter(sourceuser=existing_user).filter(targetuser__user_id=new_user_id).filter(end_observed_at=None).exists():
            print("Outgoing relationship from {} to {} already exists.".format(existing_user.screen_name, new_user_id))
            return
    else:
        if Relo.objects.filter(sourceuser__user_id=new_user_id).filter(targetuser=existing_user).filter(end_observed_at=None).exists():
            print("Incoming relationship to {} from {} already exists.".format(existing_user.screen_name, new_user_id))
            return

    r = Relo()

    if outgoing:
        existing_user.out_degree += 1
        existing_user.save()
        r.sourceuser = existing_user

        #Create new users for targets if not already in DB
        if User.objects.filter(user_id=new_user_id).exists():
            tuser = User.objects.get(user_id=new_user_id)
            tuser.in_degree = tuser.in_degree + 1
            tuser.save()
            r.targetuser = tuser
        else:
            #Creating new user object
            #u2 = add_user(user_class=0, user_data=new_user)
            #if not u2:
            #    return
            u2 = User()
            u2.user_id = new_user_id
            u2.in_degree = 1
            u2.save()
            r.targetuser = u2
    else:
            existing_user.in_degree += 1
            existing_user.save()
            r.targetuser = existing_user

            #Create new users for targets if not already in DB
            if User.objects.filter(user_id=new_user_id).exists():
                u2 = User.objects.get(user_id=new_user_id)
                u2.out_degree += 1
                u2.save()
                r.sourceuser = u2
            else:
                #Creating new user object
                #u2 = add_user(user_class=0, user_data=new_user)
                #if not u2:
                #    return
                u2 = User()
                u2.user_id = new_user_id
                u2.out_degree = 1
                u2.save()
                r.sourceuser = u2

    r.save()
    return
