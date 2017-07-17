from celery.task.control import revoke
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
import re
import pytz

from twdata import userdata
from .models import CeleryTask, User, Relo, Tweet, Hashtag, Url, Mention
from .config import FRIENDS_THRESHOLD, FOLLOWERS_THRESHOLD, STATUSES_THRESHOLD

from django.db import transaction

def kill_celery_task(task_name):
    for t in CeleryTask.objects.filter(task_name=task_name):
        print("Killing task {}: {}".format(task_name, t.celery_task_id))
        revoke(t.celery_task_id, terminate=True)
        t.delete()

def check_spam_account(user_data):
    # Reject users with high metrics - spam/celebrity/news accounts
    if user_data.followers_count > FOLLOWERS_THRESHOLD:
        return True
    if user_data.friends_count > FRIENDS_THRESHOLD:
        return True
    if user_data.statuses_count > STATUSES_THRESHOLD:
        return True
    else:
        return False

#@transaction.atomic
def add_user(user_class=0, user_data=None, **kwargs):
    # TODO: Needs to check something other than username
    # User exists as a full user (ego)
    if 'screen_name' in kwargs:
        if User.objects.filter(screen_name=screen_name).exists():
            if User.objects.get(screen_name=screen_name).user_class >= 2:
                print("User {} already exists.".format(screen_name))
                return
    # Get user_data if not supplied
    if not user_data:
        user_data=userdata.get_user(**kwargs)
    if 'screen_name' not in kwargs:
        if User.objects.filter(screen_name=user_data.screen_name).exists():
            if User.objects.get(screen_name=user_data.screen_name).user_class >= 2:
                print("User {} already exists.".format(user_data.screen_name))
                return

    if check_spam_account(user_data):
        return

    # If user is an existing node_id (alter)
    if User.objects.filter(user_id=int(user_data.id_str)).exists():
        print("Updating record...")
        # u = User.objects.filter(user_id=int(userdict.get('id_str')))
        u = get_object_or_404(User, user_id=int(user_data.id_str))
        # Update added_at, as user is upgraded from alter to ego
        u.added_at = timezone.now()
    # User is a new observation
    else:
        u = User()

    # If timezone is an issue:
    try:
        tz_aware = timezone.make_aware(user_data.created_at, timezone.get_current_timezone())
    except pytz.exceptions.AmbiguousTimeError:
        # Adding an hour to avoid DST ambiguity errors.
        time_adjusted = user_data.created_at + timedelta(minutes=60)
        tz_aware = timezone.make_aware(time_adjusted, timezone.get_current_timezone())
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
    # u.needs_phone_verification = user_data.needs_phone_verification
    #u.profile_background_color = user_data.profile_background_color
    #u.profile_background_image_url = user_data.profile_background_image_url
    #u.profile_background_image_url_https = user_data.profile_background_image_url_https
    #u.profile_background_tile = user_data.profile_background_tile
    #u.profile_image_url = user_data.profile_image_url
    #u.profile_image_url_https = user_data.profile_image_url_https
    #u.profile_link_color = user_data.profile_link_color
    # u.profile_location = user_data.profile_location
    #u.profile_sidebar_border_color = user_data.profile_sidebar_border_color
    #u.profile_sidebar_fill_color = user_data.profile_sidebar_fill_color
    #u.profile_text_color = user_data.profile_text_color
    #u.profile_use_background_image = user_data.profile_use_background_image
    u.protected = user_data.protected
    u.screen_name = user_data.screen_name
    u.statuses_count = user_data.statuses_count
    # u.suspended = user_data.suspended
    u.time_zone = user_data.time_zone
    u.translator_type = user_data.translator_type
    u.url = user_data.url
    u.user_id = int(user_data.id_str)
    u.utc_offset = user_data.utc_offset
    u.verified = user_data.verified

    u.user_class = user_class

    u.save()

    # Add relationship data if the user_class is 2 or higher
    if user_class >= 2:
        # Get users followed by account & create relationship objects
        userfollowing = userdata.friends_ids(screen_name=user_data.screen_name)
        for targetuser in userfollowing:
            create_relo(u, targetuser, outgoing=True)

        # Get followers & create relationship objects
        userfollowers = userdata.followers_ids(screen_name=user_data.screen_name)
        for sourceuser in userfollowers:
            create_relo(u, sourceuser, outgoing=False)
    return


def create_relo(existing_user, new_user_id, outgoing):

    if outgoing:
        if Relo.objects.filter(sourceuser=existing_user).filter(targetuser__user_id=new_user_id).filter(end_observed_at=None).exists():
            #print("Outgoing relationship from {} to {} already exists.".format(existing_user.screen_name, new_user_id))
            return
    else:
        if Relo.objects.filter(sourceuser__user_id=new_user_id).filter(targetuser=existing_user).filter(end_observed_at=None).exists():
            #print("Incoming relationship to {} from {} already exists.".format(existing_user.screen_name, new_user_id))
            return

    r = Relo()

    if outgoing:
        existing_user.out_degree += 1
        existing_user.save()
        r.sourceuser = existing_user

        # Create new users for targets if not already in DB
        if User.objects.filter(user_id=new_user_id).exists():
            tuser = User.objects.get(user_id=new_user_id)
            tuser.in_degree = tuser.in_degree + 1
            tuser.save()
            r.targetuser = tuser
        else:
            # Creating new user object
            # u2 = add_user(user_class=0, user_data=new_user)
            # if not u2:
            #    return
            u2 = User() #TODO: django.db.utils.IntegrityError: duplicate key value violates unique constraint "streamcollect_user_user_id_key" - May be related to deadlocking
            u2.user_id = new_user_id
            u2.in_degree = 1
            u2.save()
            r.targetuser = u2
    else:
            existing_user.in_degree += 1
            existing_user.save()
            r.targetuser = existing_user

            # Create new users for targets if not already in DB
            if User.objects.filter(user_id=new_user_id).exists():
                u2 = User.objects.get(user_id=new_user_id)
                u2.out_degree += 1
                u2.save()
                r.sourceuser = u2
            else:
                # Creating new user object
                # u2 = add_user(user_class=0, user_data=new_user)
                # if not u2:
                #    return
                u2 = User()
                u2.user_id = new_user_id
                u2.out_degree = 1
                u2.save()
                r.sourceuser = u2

    r.save()
    return


def save_user_timeline(**kwargs):
    statuses = userdata.user_timeline(**kwargs)
    #Save to DB here
    for status in statuses:
        #print('Saving Tweet: {}'.format(status.text))
        save_tweet(status)
    #map(save_tweet, statuses)
    return

def save_tweet(tweet_data):
    tweet = Tweet()
    # If timezone is an issue:
    tz_aware = timezone.make_aware(tweet_data.created_at, timezone.get_current_timezone())
    tweet.created_at = tz_aware
    tweet.favorite_count = tweet_data.favorite_count
    #tweet.filter_level = tweet_data.filter_level
    tweet.tweet_id = int(tweet_data.id_str)
    tweet.in_reply_to_status_id = tweet_data.in_reply_to_status_id # nullable
    tweet.in_reply_to_user_id = tweet_data.in_reply_to_user_id # nullable
    tweet.lang = tweet_data.lang # nullable
    #tweet.possibly_sensitive = tweet_data.possibly_sensitive # nullable
    tweet.retweet_count = tweet_data.retweet_count
    tweet.text = tweet_data.text
    try:
        tweet.coordinates_lat = tweet_data.coordinates.coordinates[1] # nullable
        tweet.coordinates_long = tweet_data.coordinates.coordinates[0]# nullable
        tweet.coordinates_type = tweet_data.coordinates.type # nullable
    except:
        pass
    try:
        tweet.quoted_status_id = tweet_data.quoted_status_id # only appears if relevant
    except:
        pass
    author_id = int(tweet_data.user.id_str)
    try:
        tweet.author = User.objects.get(user_id=author_id)
    except ObjectDoesNotExist:
        print('Author not in database, adding as new user')
        add_user(user_id=author_id)
        tweet.author = User.objects.get(user_id=author_id)
    tweet.save()

    tags = tweet_data.entities.get('hashtags')
    for tag in tags:
        save_hashtag(tag.get('text'), tweet)

    urls = tweet_data.entities.get('urls')
    for u in urls:
        # TODO: Test url cleanup, decide whether to exlude twitter urls (save elsewhere?)
        url = u.get('expanded_url')
        # Cleanup URL
        url = re.sub('(http://|https://|#.*|&.*)', '', url)
        # Exclude twitter URLs, which are added if media is attached - therefore
        # not relevant to the analysis, but look at capturing in tweet data?
        if url[0:11] != 'twitter.com':
            save_url(url, tweet)

    user_mentions = tweet_data.entities.get('user_mentions')
    for user in user_mentions:
        save_mention(user.get('screen_name'), tweet)
        # TODO: Implement something here to add these users based on authors class?
        pass

    # TODO: save other entities?: media, user_mentions, symbols, extended_entities
    # https://dev.twitter.com/overview/api/entities-in-twitter-objects
    return


def save_hashtag(hashtag_text, tweet_object):
    hashtag_text = hashtag_text.lower()
    hashtag, created = Hashtag.objects.get_or_create(hashtag=hashtag_text)
    if created:
        hashtag.save()
    hashtag.tweets.add(tweet_object)
    return


def save_url(url_text, tweet_object):
    url, created = Url.objects.get_or_create(url=url_text)
    if created:
        url.save()
    url.tweets.add(tweet_object)
    return


def save_mention(mention_text, tweet_object):
    mention_text = mention_text.lower()
    mention, created = Mention.objects.get_or_create(mention=mention_text)
    if created:
        mention.save()
    mention.tweets.add(tweet_object)
    return
