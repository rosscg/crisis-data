from celery.task.control import revoke
from django.shortcuts import get_object_or_404
from django.utils import timezone

from twdata import userdata
from .models import CeleryTask, User, Relo
from .config import FRIENDS_THRESHOLD, FOLLOWERS_THRESHOLD, STATUSES_THRESHOLD

def kill_celery_task(task_name):
    for t in CeleryTask.objects.filter(task_name=task_name):
        print("Killing task {}: {}".format(task_name, t.celery_task_id))
        revoke(t.celery_task_id, terminate=True)
        t.delete()

def check_spam_account(user_data):
    # Reject users with high metrics - spam/celebrity/news accounts
    #print("Checking user as spam: {}".format(user_data.screen_name))
    if user_data.followers_count > FOLLOWERS_THRESHOLD:
        print('Rejecting user {} with high follower count: {}'.format(user_data.screen_name, user_data.followers_count))
        return True
    if user_data.friends_count > FRIENDS_THRESHOLD:
        print('Rejecting user {} with high friends count: {}'.format(user_data.screen_name, user_data.friends_count))
        return True
    if user_data.statuses_count > STATUSES_THRESHOLD:
        print('Rejecting user {} with high status count: {}'.format(user_data.screen_name, user_data.statuses_count))
        return True
    else:
        print("User {} passed spam test.".format(user_data.screen_name))
        return False

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
