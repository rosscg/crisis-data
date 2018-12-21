#from celery.task.control import revoke
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
import re
import pytz

from datetime import timedelta
from dateutil.parser import *

from twdata import userdata
#from .tasks import save_media_task
from .models import Event, User, Relo, Tweet, Place, Hashtag, Url, Mention, Keyword
from .config import FRIENDS_THRESHOLD, FOLLOWERS_THRESHOLD, STATUSES_THRESHOLD, TAG_OCCURENCE_THRESHOLD, MENTION_OCCURENCE_THRESHOLD, DOWNLOAD_MEDIA, MAX_REPLY_DEPTH

from django.db import transaction
from django.db.models import Count
from urllib.request import urlopen # To unwind URLs # TODO: Consider updating to requests package instead

# For downloading media:
from urllib.request import urlretrieve # TODO: Consider updating to requests package instead
import urllib.parse as urlparse
from bs4 import BeautifulSoup
import os


# TODO: move this?
def batch_qs(qs, batch_size=10):
    """
    Returns a (start, end, total, queryset) tuple for each batch in the given
    queryset.

    Usage:
        # Must order queryset
        article_qs = Article.objects.order_by('id')
        for start, end, total, qs in batch_qs(article_qs):
            print("Now processing {}-{} of {}".format(start + 1, end, total))
            for article in qs:
                print(article.body)
    """
    total = qs.count()
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        yield (start, end, total, qs[start:end])


# Check for users who have updated their Twitter screen names, or have been
# deleted/suspended since the first observation.
def update_screen_names(users=None):
    print('Updating Screen Names...')

    if users is None:
        users = list(User.objects.filter(user_class__gte=2).values_list('user_id', flat=True))
    length = len(users)
    chunk_size = 100 # Max of 100
    index = 0
    c = 0 # total changed
    deleted_users = list(users)

    # Requesting User objects in batches to minimise API limits
    while index < length:
        if length - index <= chunk_size:
            end = length
        else:
            end = index + chunk_size
        chunk = users[index:end]
        print("Length: {}, Chunk: {}:{}".format(length, index, end))
        #process chunk
        user_list = userdata.lookup_users(user_ids=chunk)
        if not user_list:
            # False returned if only dead users in list
            index += chunk_size
            continue
        for live_u in user_list:
            deleted_users.remove(int(live_u.id_str))
            u = User.objects.get(user_id=int(live_u.id_str))
            if live_u.screen_name != u.screen_name:
                print('New screen name for user: {} - {}.'.format(u.screen_name, live_u.screen_name))
                if u.old_screen_name is None:
                    u.old_screen_name = u.screen_name
                u.screen_name = live_u.screen_name
                u.save()
                c += 1
        index += chunk_size

    for deleted_id in deleted_users:
        u = User.objects.get(user_id=deleted_id)
        if u.is_deleted == False:
            u.is_deleted = True
            u.is_deleted_observed = timezone.now()
            u.save()

    print('{} users changed names out of {} total.'.format(c, len(users)))
    print('{} deleted or suspended users.'.format(len(deleted_users)))
    return


def check_deleted_tweets(id_list=None):
    print('Checking existing Tweets for deletion...')

    if id_list is None:
        id_list = list(Tweet.objects.filter(data_source__gte=1).values_list('tweet_id', flat=True))

    length = len(id_list)
    chunk_size = 100 # Max of 100
    index = 0
    deleted_tweets = list(id_list)

    # Requesting Tweet objects in batches to minimise API limits
    while index < length:
        if length - index <= chunk_size:
            end = length
        else:
            end = index + chunk_size
        chunk = id_list[index:end]
        print("Length: {}, Chunk: {}:{}".format(length, index, end))
        #process chunk
        tweet_list = userdata.statuses_lookup(chunk)
        if not tweet_list:
            index += chunk_size
            continue
        for live_t in tweet_list:
            deleted_tweets.remove(int(live_t.id_str))
        index += chunk_size

    for deleted_id in deleted_tweets:
        t = Tweet.objects.get(tweet_id=deleted_id)
        if t.is_deleted == False:
            t.is_deleted = True
            t.is_deleted_observed = timezone.now()
            t.save()

    print('{} deleted or hidden Tweets of total: {}.'.format(len(deleted_tweets), length))
    return


def check_spam_account(user_data):
    if user_data == False:
        return
    # Reject users with high metrics - spam/celebrity/news accounts
    if user_data.followers_count > FOLLOWERS_THRESHOLD:
        pass
    if user_data.friends_count > FRIENDS_THRESHOLD:
        pass
    if user_data.statuses_count > STATUSES_THRESHOLD:
        pass
    else:
        return False

    #TODO: Testing users for validity of this setting choice:
    with open('users_rejected_as_spam.txt', 'a') as f:
        print('{}, {}, {}, {}, {}'.format(user_data.screen_name, user_data.id_str, user_data.followers_count, user_data.friends_count, user_data.statuses_count), file=f)
    f.close()
    return True


# Automatically add new tags to the tracking list based on whether they meet the TAG_OCCURENCE_THRESHOLD
# Requires stream to be periodically restarted.
# Currently adds as low-priority, may need to reconsider.
def update_tracked_tags():
    print('updating tracked tags')
    #If a hashtag appears in x% of tweets, add as a keyword to track.
    hashtags_with_counts = Hashtag.objects.all().annotate(tweet_count=Count('tweets__id'))
    tweet_count = len(Tweet.objects.all())
    threshold = (tweet_count*TAG_OCCURENCE_THRESHOLD)

    temp_dic = {}
    keywords = Keyword.objects.all().values_list('keyword', flat=True)

    for tag in hashtags_with_counts:
        if tag.hashtag not in keywords:
            temp_dic[tag.hashtag]=tag.tweet_count
        if tag.tweet_count > threshold:
            hashtag = '#' + tag.hashtag
            try:
                k = Keyword()
                k.keyword = hashtag.lower()
                k.created_at = timezone.now()
                k.priority = 1
                k.save()
                print('Adding new hashtag to keyword list: {}'.format(hashtag))
            except:
                #print('Error keyword list: {} Likely already exists.'.format(hashtag))
                pass

    # Print most common tags
    top = sorted(temp_dic.items(), key=lambda x:x[1], reverse=True)[0:5]
    print(top)
    print('Total tweets: {}'.format(tweet_count))


def add_users_from_mentions():
    #If a mention appears in x% of tweets, add as a user_class=2. #TODO: Sould this use a different user_class?
    mentions_with_counts = Mention.objects.all().annotate(tweet_count=Count('tweets__id'))
    tweet_count = len(Tweet.objects.all())
    threshold = (tweet_count*MENTION_OCCURENCE_THRESHOLD)

    for user in mentions_with_counts:
        if user.tweet_count > threshold:
            print('Adding new user from mentions: {}'.format(user.mention))
            add_user(user_class=2, data_source=0, screen_name=user.mention)
    return


#@transaction.atomic
def add_user(user_class=0, user_data=None, data_source=0, **kwargs):
    # User exists at the user_class level
    if 'screen_name' in kwargs:
        screen_name=kwargs.get('screen_name')
        try:
            u = User.objects.get(screen_name=screen_name)
            if u.user_class >= user_class:
                print('User {} already exists.'.format(u.screen_name))
                if u.data_source < data_source:
                    u.data_source = data_source
                    u.save()
                return u
        except:
            pass
    # Get user_data if not supplied
    if not user_data:
        user_data=userdata.get_user(**kwargs)
    #if check_spam_account(user_data): #TODO: Excluded for testing, only possible while Relos aren't created automatically.
    #    return False
    try:
        u # exists? i.e. made with screen_name call above.
    except:
        try:
            u = User.objects.get(user_id=int(user_data.id_str))
        except:
            u = User()
    # Check if user already exists class level. None is true if the user hasn't
    # been saved yet (i.e. created in this function)
    if not u.user_class == None and u.user_class >= user_class:
        print('User {} already exists.'.format(u.screen_name))
        if u.data_source < data_source:
            u.data_source = data_source
            u.save()
        return u
    # If timezone is an issue:
    u.added_at = timezone.now()
    try:
        tz_aware = timezone.make_aware(user_data.created_at, timezone=pytz.utc)
    except pytz.exceptions.AmbiguousTimeError:
        # Adding an hour to avoid DST ambiguity errors.
        time_adjusted = user_data.created_at + timedelta(minutes=60)
        tz_aware = timezone.make_aware(time_adjusted, timezone=pytz.utc)
    u.created_at = tz_aware

    u.default_profile = user_data.default_profile
    u.default_profile_image = user_data.default_profile_image
    u.description = user_data.description
    u.favourites_count = user_data.favourites_count
    u.followers_count = user_data.followers_count
    u.friends_count = user_data.friends_count
    u.geo_enabled = user_data.geo_enabled
    #u.has_extended_profile = user_data.has_extended_profile      # not returned in user object attached to Tweet, requires API request
    #u.is_translation_enabled = user_data.is_translation_enabled    # not returned in user object attached to Tweet, requires API request
    u.lang = user_data.lang
    u.listed_count = user_data.listed_count
    u.location = user_data.location
    u.name = user_data.name
    #u.needs_phone_verification = user_data.needs_phone_verification
    #u.profile_background_color = user_data.profile_background_color
    #u.profile_background_image_url = user_data.profile_background_image_url
    #u.profile_background_image_url_https = user_data.profile_background_image_url_https
    #u.profile_background_tile = user_data.profile_background_tile
    #u.profile_image_url = user_data.profile_image_url
    #u.profile_image_url_https = user_data.profile_image_url_https
    #u.profile_link_color = user_data.profile_link_color
    #u.profile_location = user_data.profile_location
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
    u.data_source = data_source
    #u.save()

    # Add relationship data if the user_class is 2 or higher
    if user_class >= 2:     # TODO: Storing in DB rather than creating objects to reduce DB load, can create later. Affects observing new/dead relationships.
        # Get users followed by account & create relationship objects
        try:
            user_following = userdata.friends_ids(screen_name=user_data.screen_name)
        except:
            return False
        if user_following:
            u.user_following = user_following

        #for target_user in user_following:
        #    create_relo(u, target_user, outgoing=True)
        # Get followers & create relationship objects
        try:
            user_followers = userdata.followers_ids(screen_name=user_data.screen_name)
        except:
            return False
        if user_followers:
            u.user_followers = user_followers
        #for source_user in user_followers:
        #    create_relo(u, source_user, outgoing=False)
    u.save()
    return u


#TODO: Have commented out the updates to the in/out degree rows (to reduce db calls). Decide whether to remove.
def create_relo(existing_user, new_user_id, outgoing, observed=timezone.now()):
    # TODO: may be able to remove these checks by using unique_together in the Relo model and a try/except clause when saving the Relo here.
    if outgoing: # existing_user is following new_user_id
        if Relo.objects.filter(source_user=existing_user).filter(target_user__user_id=new_user_id).filter(end_observed_at=None).exists():
            return
    else: # new_user_id is following existing_user
        if Relo.objects.filter(source_user__user_id=new_user_id).filter(target_user=existing_user).filter(end_observed_at=None).exists():
            return
    r = Relo()
    r.observed_at = observed
    if outgoing:
        #existing_user.out_degree += 1
        #existing_user.save()
        r.source_user = existing_user
        # Create new users for targets if not already in DB
        try:
            tuser = User.objects.get(user_id=new_user_id)
        except:
            tuser = User()
            tuser.added_at = timezone.now()
            tuser.user_id = new_user_id
            tuser.user_class=0
#TODO: Replace try/except block with get_or_create, then test. Add if statement for save()
#        tuser, created = User.objects.get_or_create(
#            user_id=new_user_id,
#            defaults={'added_at': timezone.now(), 'user_class': 0, 'in_degree': 1}
#        )
#       if not created: # Wrap next two lines, as new users don't need += 1
        tuser.in_degree += 1
        tuser.save()
        r.target_user = tuser
    else: # Incoming relationship
        #existing_user.in_degree += 1
        #existing_user.save()
        r.target_user = existing_user
        # Create new users for targets if not already in DB
        try:
            suser = User.objects.get(user_id=new_user_id)
        except:
            suser = User()
            suser.added_at = timezone.now()
            suser.user_id = new_user_id
            suser.user_class=0
#TODO: Replace try/except block with get_or_create, then test.
#        suser, created = User.objects.get_or_create(
#            user_id=new_user_id,
#            defaults={'added_at': timezone.now(), 'user_class': 0, 'out_degree' : 0}
#        )
#       if not created: # Wrap next two lines, as new users don't need += 1
        suser.out_degree += 1
        suser.save()
        r.source_user = suser
    r.save()
    return


# Move relationship information from temporary user_following (etc.) list to Relo object.
# TODO: Consider summing in/out degrees here for speed when building network ?
def create_relos_from_list():
    # Get users which have a populated list to turn into objects.
    users_qs = User.objects.filter(user_class__gte=2).filter(Q(user_followers__isnull=False) | Q(user_following__isnull=False) | Q(user_followers_update__isnull=False) | Q(user_following_update__isnull=False)).order_by('id')

    print('Creating relationship object sets for {} users.'.format(users_qs.count()))

    for start, end, total, qs in batch_qs(users_qs):
        print("Now processing {}-{} of {}".format(start + 1, end, total))
        for user in qs:
            ##########################################
            ##########################################
            ########################################## Temporary 'spam' exclusion for speed:
            try:
                if len(user.user_following) > FRIENDS_THRESHOLD:
                    print('User {} friends exceeds threshold'.format(user.screen_name))
                    continue
            except:
                pass
            try:
                if len(user.user_followers) > FOLLOWERS_THRESHOLD:
                    print('User {} followers exceeds threshold'.format(user.screen_name))
                    continue
            except:
                pass
            ##########################################
            ##########################################

            print('Creating Relationship Objects for User: {}'.format(user.screen_name))
            tweets = user.tweet.filter(data_source__gte=1).order_by('created_at')
            earliest_streamed_tweet_time = tweets[0].created_at
            if user.user_following is not None:
                for new_following_id in user.user_following:
                    create_relo(user, new_following_id, outgoing=True, observed=earliest_streamed_tweet_time)
            if user.user_followers is not None:
                for new_follower_id in user.user_followers:
                    create_relo(user, new_follower_id, outgoing=False, observed=earliest_streamed_tweet_time)

            try:
                new_friend_links = [a for a in user.user_following_update if (a not in user.user_following)]
                dead_friend_links = [a for a in user.user_following if (a not in user.user_following_update)]
            except:
                new_friend_links = []
                dead_friend_links = []

            for target_user_id in dead_friend_links:
                for ob in Relo.objects.filter(source_user=user, target_user__user_id__contains=target_user_id).filter(end_observed_at=None):
                    ob.end_observed_at = user.user_network_update_observed_at
                    ob.save()
                tuser = User.objects.get(user_id=target_user_id)
                tuser.in_degree = tuser.in_degree - 1
                tuser.save()
                #Commented out to reduce DB calls:
                #user.out_degree -= 1
                #user.save()
            for target_user in new_friend_links:
                create_relo(user, target_user, outgoing=True, observed=user.user_network_update_observed_at)

            try:
                new_follower_links = [a for a in user.user_followers_update if (a not in user.user_followers)]
                dead_follower_links = [a for a in user.user_followers if (a not in user.user_followers_update)]
            except:
                new_follower_links = []
                dead_follower_links = []

            for source_user_id in dead_follower_links:
                for ob in Relo.objects.filter(target_user=user, source_user__user_id__contains=source_user_id).filter(end_observed_at=None):
                    ob.end_observed_at = user.user_network_update_observed_at
                    ob.save()
                suser = User.objects.get(user_id=source_user_id)
                suser.in_degree = suser.in_degree - 1
                suser.save()
                #Commented out to reduce DB calls:
                #user.in_degree -= 1
                #user.save()
            for source_user in new_follower_links:
                create_relo(user, source_user, outgoing=False, observed=user.user_network_update_observed_at)

            # TODO: Decide whether to delete the list or keep for speed when building networks:
            #user.user_following = None
            #user.user_followers = None
            #user.user_following_update = None
            #user.user_followers_update = None
            #user.user_network_update_observed_at = None
            #user.save()

    return


def save_user_timelines():
    try:
        event = Event.objects.all()[0]
    except:
        return
    start_time = event.time_start
    end_time = event.time_end
    if start_time == None or end_time == None:
        print("No start/end time detected, add to event manually.")
        return

    users = User.objects.filter(user_class__gte=2)[4210:] # TODO: temp slice
    user_count = users.count()
    progress_count = 0

    for user in users:
        print('Saving timeline for user: {}'.format(user.screen_name))
        timeline_old_enough = False # received timeline encompasses start_time
        max_id = False
        if progress_count % 10 == 0:
            print('Progress: {} of {}'.format(progress_count, user_count))
        progress_count += 1
        while timeline_old_enough is False:
            if max_id is False:
                statuses = userdata.user_timeline(id=user.user_id)
            else:
                statuses = userdata.user_timeline(id=user.user_id, max_id=max_id)
            if statuses is False:
                print('Timeline error with user: {}'.format(user.screen_name))
                timeline_old_enough = True
                break
            #Save to DB here
            for status in statuses:
                if int(status.id_str) < max_id or max_id is False:
                    max_id = int(status.id_str)
                tz_aware = timezone.make_aware(status.created_at, timezone=pytz.utc)
                if tz_aware > start_time:
                    if tz_aware < end_time:
                        try:
                            if status.truncated:
                                text=status.extended_tweet.get('full_text')
                            else:
                                try:
                                    text=status.full_text
                                except:
                                    text=status.text
                            save_tweet(status, data_source=0, reply_depth=99) # Don't save any replied to statuses
                        except:
                            pass
                    else:
                        #print('Tweet too new.')
                        max_id = int(status.id_str)
                else:
                    #print('Tweet too old.')
                    timeline_old_enough = True
            if len(statuses) < 200:
                timeline_old_enough = True
    return


def save_tweet(tweet_data, data_source, user_class=0, save_entities=False, reply_depth=0):

    if data_source == 0 or user_class == 0: # ie. Tweet not from original stream
        try:
            tweet = Tweet.objects.get(tweet_id=int(tweet_data.id_str)) # TODO: This may be too slow, faster to just try and save Tweet, catch duplicate exception ?
        except ObjectDoesNotExist:
            pass
        else:
            print('Tweet already exists')
            return tweet

    tweet = Tweet()
    # If timezone is an issue:
    tz_aware = timezone.make_aware(tweet_data.created_at, timezone.get_current_timezone())
    tweet.created_at = tz_aware
    tweet.favorite_count = tweet_data.favorite_count
    #tweet.filter_level = tweet_data.filter_level
    tweet.tweet_id = int(tweet_data.id_str)
    tweet.lang = tweet_data.lang # nullable
    #tweet.possibly_sensitive = tweet_data.possibly_sensitive # nullable
    tweet.retweet_count = tweet_data.retweet_count
    tweet.source = tweet_data.source
    tweet.data_source = data_source

    try:
        tweet.text = tweet_data.extended_tweet.get('full_text') # Truncated Tweets from replies or quotes don't return extended_tweet
    except:
        # Try block to handle current issue with REST calls and extended_tweet
        try:
            tweet.text=tweet_data.full_text
        except:
            tweet.text=tweet_data.text
    try:
        tweet.coordinates_lat = tweet_data.coordinates.get('coordinates')[1] # nullable
        tweet.coordinates_lon = tweet_data.coordinates.get('coordinates')[0] # nullable
        tweet.coordinates_type = tweet_data.coordinates.get('type') # nullable
    except:
        pass
    if tweet_data.in_reply_to_status_id_str:
        tweet.in_reply_to_status_id = int(tweet_data.in_reply_to_status_id_str) # nullable
        tweet.in_reply_to_user_id = int(tweet_data.in_reply_to_user_id_str) # nullable

        if reply_depth <= MAX_REPLY_DEPTH:   # Save replies to depth set in config.
            reply_depth += 1
            reply_status = userdata.statuses_lookup([int(tweet_data.in_reply_to_status_id_str)], trim_user=False)
            if len(reply_status) > 0: # If replied_to is returned (ie. not deleted)
                reply_status = reply_status[0]
                #print('Saving reply at depth = {}'.format(reply_depth))
                replied_to_status = save_tweet(reply_status, user_class=0, save_entities=save_entities, data_source=0, reply_depth=reply_depth)
                if replied_to_status:
                    tweet.replied_to_status = replied_to_status
            else:
                print('error with tweet reply: {}'.format(tweet_data.in_reply_to_status_id_str)) #TODO: testing, remove

    try:
        tweet.quoted_status_id_int = int(tweet_data.quoted_status_id_str) # Only appears when relevant
        try:
            qt = tweet_data.quoted_status
        except:
            #print('tweet has quoted_status_id_str but not quoted_status') #TODO: Test. I beleive this is due to a 'nested' quote, the second quote won't be contained in the packet.
            #print(tweet_data)
            pass
    except:
        pass
    try: # Saving quoted Tweet
        quoted = tweet_data.quoted_status
    except:
        pass
    else:
        quoted_status = save_tweet(quoted, user_class=0, save_entities=save_entities, data_source=0)
        if quoted_status:
            tweet.quoted_status = quoted_status

    author_id = int(tweet_data.user.id_str)
    try:
        tweet.author = User.objects.get(user_id=author_id)
    except ObjectDoesNotExist:
        #print('Author not in database, adding as new user')
        user = add_user(user_data=tweet_data.user, data_source=data_source, user_class=user_class)
        if user:
            tweet.author = user
        else:
            # User is detected as a spam account, therefore Tweet not saved. If pursuing a reply chain, it is halted.
            return
    if tweet_data.place is not None:
        tweet.place = save_place(tweet_data.place)
    tweet.save()

    if save_entities:
        tags = tweet_data.entities.get('hashtags')
        for tag in tags:
            save_hashtag(tag.get('text'), tweet)
        urls = tweet_data.entities.get('urls')
        for u in urls:
            # TODO: Test url cleanup, decide whether to exlude twitter urls (save elsewhere?)
            url = u.get('expanded_url')
            save_url(url, tweet)
        user_mentions = tweet_data.entities.get('user_mentions')
        for user in user_mentions:
            save_mention(user.get('screen_name'), tweet)
            # TODO: Implement something here to add these users based on authors class?
            pass

    #if DOWNLOAD_MEDIA and save_entities:    # TODO: This should check tweet doesn't already exist first, otherwise waste of resources.
        #save_media_task.delay(tweet, tweet_data)
        #filenames, type = download_media(tweet_data)
        # TODO: Decide how to link to tweet object - use a relation or three fields (base_name, type, count)
        #if len(filenames) > 0:
        #    tweet.media_files = filenames
        #    tweet.media_files_type = type
        #tweet.save()

    return tweet

#This is currently unused (replicated in tasks.py)
def download_media(tweet_data):
    event = Event.objects.all()[0].name
    media_type = ''
    media_url = []

    print('Saving data from source: {}'.format(tweet_data.source))

    if tweet_data.source == 'Instagram':
        try:
            urls = tweet_data.extended_tweet.get('entities').get('urls')   # Works for Extended data from stream
            last_index = 0
            for u in urls: # URLs posted in comments are returned in entities. Finding last occuring (i.e. source).
                if u.get('indices')[0] >= last_index:
                    last_index = u.get('indices')[0]
                    insta_url = u.get('expanded_url')
        except:
            urls = tweet_data.entities.get('urls')    # Works for Extended data from REST (to test)
            last_index = 0
            for u in urls:
                if u.get('indices')[0] >= last_index:
                    last_index = u.get('indices')[0]
                    insta_url = u.get('expanded_url') #TODO: move these 5 lines outside of block, as they are repeated. May have to check they don't throw errors too.
        insta_url = 'https://www.instagram.com/p/' + insta_url.split('/')[4]
        try:
            response = urlopen(insta_url)
        except:
            print('Error with Instagram media: {}, likely deleted.'.format(insta_url))
            return([], '')
        try:
            page_source = response.read()
        except Exception as e:
            print(e)
            return([], '')
            #raise   #TODO: Handle connection reset here
            # TODO: if above error not important, fold this try into above with:
            # response = urlopen(insta_url).read()
        soup = BeautifulSoup(page_source, 'html.parser')

        insta_image = soup.find_all("meta", property="og:image")
        insta_vid = soup.find_all("meta", property="og:video")
        if insta_vid:
            media_type = 'video'
            media_url.append(insta_vid[0]["content"])
        else:
            media_type = 'image'
            media_url.append(insta_image[0]["content"])
        path = urlparse.urlparse(media_url[0]).path
        ext = path[len(path)-4:] # Remove trailing queries etc

    else:   # Tweet media
        try:
            media_type = tweet_data.extended_entities.get('media')[0].get('type')
        except:
            return([], '') #TODO: Test these don't have media

        if media_type == 'video': # Twitter Video:
            highest_bitrate = 0
            variants = tweet_data.extended_entities.get('media')[0].get('video_info').get('variants')
            for v in variants:
                if v.get('bitrate') is not None and v.get('bitrate') >= highest_bitrate:
                    highest_bitrate = v.get('bitrate')
                    highest_url = v.get('url')
            media_url.append(highest_url)
            path = urlparse.urlparse(media_url[0]).path
            ext = path[len(path)-4:] # Remove trailing queries etc

            if highest_bitrate == 0:
                media_type = 'gif'

        elif media_type == 'photo':
            media_items = tweet_data.extended_entities.get('media')
            for m in media_items:
                media_url.append(m.get('media_url'))
            media_type = 'image'
            path = urlparse.urlparse(media_items[0].get('media_url')).path
            ext = path[len(path)-4:] # Remove trailing queries etc

        elif media_type == 'animated_gif':
            variants = tweet_data.extended_entities.get('media')[0].get('video_info').get('variants')[0].get('url')
            media_type = 'gif'
            media_url.append(variants)
            path = urlparse.urlparse(media_url[0]).path
            ext = path[len(path)-4:] # Remove trailing queries etc

        else:
            if tweet_data.extended_entities.get('media') is not None:
                print('Unhandled Twitter media type: {}'.format(tweet_data.extended_entities.get('media')[0].get('type')))
                print(tweet_data)
            return([], '')

    directory = './' + event + '_media/' + media_type + '/'
    if not os.path.exists(directory):
        os.makedirs(directory)

    base_filename = tweet_data.author.id_str + '_' + tweet_data.id_str
    saved_files = []
    if len(media_url) > 0:
        i=0
        for m in media_url:
            filename = base_filename
            if len(media_url) > 1:
                filename = base_filename + '_' + str(i)
            urlretrieve(m, directory + filename  + str(ext))
            saved_files.append(filename + str(ext))
            i += 1
    return(saved_files, media_type)


def save_place(place_data):
    place, created = Place.objects.get_or_create(
        place_id = place_data.id
        )
    if created:     #TODO: Test. Moved outside of get_or_create to attempt to improve speed. Required setting these as null=true in model.
        place.url = place_data.url
        place.place_type = place_data.place_type
        place.name = place_data.name
        place.full_name = place_data.full_name
        place.country_code = place_data.country_code
        place.country = place_data.country
        place.lon_1 = place_data.bounding_box.coordinates[0][0][0]
        place.lat_1 = place_data.bounding_box.coordinates[0][0][1]
        place.lon_2 = place_data.bounding_box.coordinates[0][1][0]
        place.lat_2 = place_data.bounding_box.coordinates[0][1][1]
        place.lon_3 = place_data.bounding_box.coordinates[0][2][0]
        place.lat_3 = place_data.bounding_box.coordinates[0][2][1]
        place.lon_4 = place_data.bounding_box.coordinates[0][3][0]
        place.lat_4 = place_data.bounding_box.coordinates[0][3][1]
        place.save()
        print('Saving place: {}'.format(place.name))
    return place


def save_hashtag(hashtag_text, tweet_object):
    hashtag_text = hashtag_text.lower()
    hashtag, created = Hashtag.objects.get_or_create(hashtag=hashtag_text)
    #if created:
    #    hashtag.save()      # TODO: Is this save necessary? Should be part of get_or_create
    hashtag.tweets.add(tweet_object)
    return


def save_url(url_text, tweet_object):
    stripped = re.sub('(http://|https://|#.*|&.*)', '', url_text)
    if stripped[:11] == 'twitter.com' and stripped[:25] is not 'twitter.com/i/web/status/':
        with open('ignored_tw_urls_log.txt', 'a') as f:
            print('Pre-unwound: {}'.format(url_text), file=f)
        f.close()
        return

    try:
        resp = urlopen(url_text)
        unwound = resp.url  # TODO: need to unwind more than once?
    except:
        unwound = url_text
    unwound = re.sub('(http://|https://|#.*|&.*)', '', unwound)
    # Exclude twitter URLs, which are added if media is attached - therefore
    # not relevant to the analysis. TODO: Check whether this is working as intended.
    if unwound[0:11] == 'twitter.com' and unwound[:25] is not 'twitter.com/i/web/status/':  # TODO: Should be able to remove this check, as it is done earlier
        with open('ignored_tw_urls_log.txt', 'a') as f:
            print(unwound, file=f)
            print('Original: {}'.format(stripped), file=f)
        f.close()
        return
    url, created = Url.objects.get_or_create(url=unwound)
    #if created:
    #    url.save()
    url.tweets.add(tweet_object)
    return


def save_mention(mention_text, tweet_object):
    mention_text = mention_text.lower()
    mention, created = Mention.objects.get_or_create(mention=mention_text)
    #if created:
    #    mention.save()
    mention.tweets.add(tweet_object)
    return
