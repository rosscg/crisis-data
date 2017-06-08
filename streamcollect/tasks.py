from celery import shared_task
from celery.task import periodic_task

from twdata import userdata
from .models import User, Relo
from dateutil.parser import *
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta


#TODO: Replace into target method. NOTE: This will have a concurrency problem where API limit waiting may lead to overlap of tasks.
#@periodic_task(run_every=timedelta(hours=1))
def update_user_relos_periodic():
    update_user_relos_task()
    return


@shared_task
def add_user_task(**kwargs):
    userdict = userdata.get_user(**kwargs)

    # Reject users with high metrics - spam/celebrity/news accounts
    if userdict.get('followers_count') > 5000:
        print('Rejecting user with high follower count: {}'.format(userdict.get('followers_count')))
        return
    if userdict.get('friends_count') > 5000:
        print('Rejecting user with high friends count: {}'.format(userdict.get('friends_count')))
        return
    if userdict.get('statuses_count') > 10000:
        print('Rejecting user with high status count: {}'.format(userdict.get('statuses_count')))
        return

    #See if user exists as a full user, or an existing target node.
    if User.objects.filter(screen_name=userdict.get('screen_name')).exists():
        print("User {} already exists.".format(kwargs))

    else:
        #If user is an existing node_id
        if User.objects.filter(user_id=int(userdict.get('id_str'))).exists():

            #Updating user object
            print("Updating record...")
            #u = User.objects.filter(user_id=int(userdict.get('id_str')))
            u = get_object_or_404(User, user_id=int(userdict.get('id_str')))

            #TODO REMOVE THIS
            u.relevant_in_degree = u.relevant_in_degree + 5

        #User is a new observation
        else:
            #Creating user object
            print("Creating record...")
            u = User()

            #TODO REMOVE THIS
            u.relevant_in_degree = 5

        u.created_at = parse(userdict.get('created_at'))
        u.default_profile = userdict.get('default_profile')
        u.default_profile_image = userdict.get('default_profile_image')
        u.description = userdict.get('description')
        #TODO entities = NOT YET IMPLEMENTED
        u.favourites_count = userdict.get('favourites_count')
        u.followers_count = userdict.get('followers_count')
        u.friends_count = userdict.get('friends_count')
        u.geo_enabled = userdict.get('geo_enabled')
        u.has_extended_profile = userdict.get('has_extended_profile')
        u.is_translation_enabled = userdict.get('is_translation_enabled')
        u.lang = userdict.get('lang')
        u.listed_count = userdict.get('listed_count')
        u.location = userdict.get('location')
        u.name = userdict.get('name')
        u.needs_phone_verification = userdict.get('needs_phone_verification')
        u.profile_background_color = userdict.get('profile_background_color')
        u.profile_background_image_url = userdict.get('profile_background_image_url')
        u.profile_background_image_url_https = userdict.get('profile_background_image_url_https')
        u.profile_background_tile = userdict.get('profile_background_tile')
        u.profile_image_url = userdict.get('profile_image_url')
        u.profile_image_url_https = userdict.get('profile_image_url_https')
        u.profile_link_color = userdict.get('profile_link_color')
        u.profile_location = userdict.get('profile_location')
        u.profile_sidebar_border_color = userdict.get('profile_sidebar_border_color')
        u.profile_sidebar_fill_color = userdict.get('profile_sidebar_fill_color')
        u.profile_text_color = userdict.get('profile_text_color')
        u.profile_use_background_image = userdict.get('profile_use_background_image')
        u.protected = userdict.get('protected')
        u.screen_name = userdict.get('screen_name')
        u.statuses_count = userdict.get('statuses_count')
        u.suspended = userdict.get('suspended')
        u.time_zone = userdict.get('time_zone')
        u.translator_type = userdict.get('translator_type')
        u.url = userdict.get('url')
        u.user_id = int(userdict.get('id_str'))
        u.utc_offset = userdict.get('utc_offset')
        u.verified = userdict.get('verified')

        u.save()

        #Get users followed by account & create relationship objects
        userfollowing = userdata.friends_ids(screen_name = userdict.get('screen_name'))
        for targetuser in userfollowing:
            create_relo(u, targetuser, outgoing=True)

        #Get followers & create relationship objects
        userfollowers = userdata.followers_ids(screen_name = userdict.get('screen_name'))
        for sourceuser in userfollowers:
            create_relo(u, sourceuser, outgoing=False)
    return


#TODO: add user_followed_by functionality
@shared_task
def update_user_relos_task():
    users = User.objects.filter(screen_name__isnull=False)

    for user in users:
        #Get users followed by account
        user_following = userdata.friends_ids(screen_name = user.screen_name)

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
            tuser.relevant_in_degree = tuser.relevant_in_degree - 1
            tuser.save()

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
            suser.relevant_in_degree = suser.relevant_in_degree - 1
            suser.save()

        for source_user in new_follower_links:
            create_relo(user, source_user, outgoing=False)

    return

#TODO: move this elsewhere and import?
def create_relo(existing_user, new_user_id, outgoing):

    r = Relo()

    if outgoing:
        r.sourceuser = existing_user

        #Create new users for targets if not already in DB
        if User.objects.filter(user_id=new_user_id).exists():
            tuser = User.objects.get(user_id=new_user_id)
            tuser.relevant_in_degree = tuser.relevant_in_degree + 1
            tuser.save()
            r.targetuser = tuser

        else:
            u2 = User()
            u2.user_id = new_user_id
            u2.relevant_in_degree = 1
            u2.save()
            r.targetuser = u2
    else:
            r.targetuser = existing_user

            #Create new users for targets if not already in DB
            if User.objects.filter(user_id=new_user_id).exists():
                r.sourceuser = User.objects.get(user_id=new_user_id)
            else:
                u2 = User()
                u2.user_id = new_user_id
                u2.save()
                r.sourceuser = u2

    r.save()
    return
