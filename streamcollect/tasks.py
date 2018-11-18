from celery import shared_task
from celery.task import periodic_task
from datetime import timedelta
import pytz
from django.utils import timezone
from django.db.models import Q

from twdata import userdata
from .models import User, Relo, Event

from .methods import check_spam_account, add_user, create_relo, save_tweet, update_tracked_tags, save_user_timelines, update_screen_names, check_deleted_tweets#, download_media
from .config import REQUIRED_IN_DEGREE, REQUIRED_OUT_DEGREE, DOWNLOAD_MEDIA

# For downloading media:
from urllib.request import urlretrieve, urlopen
import urllib.parse as urlparse
from bs4 import BeautifulSoup
import os


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
    update_tracked_tags()   #Requires config.py: REFRESH_STREAM=True
    #add_users_from_mentions()
    return

#TODO: Consider adding processing tasks to a new, third queue. Add in all the Views inspect lists

@shared_task(bind=True, name='tasks.save_user_timelines', queue='save_object_q')
def save_user_timelines_task(self):
    save_user_timelines()
    return


@shared_task(bind=True, name='tasks.trim_spam_accounts', queue='save_object_q')
def trim_spam_accounts(self):
    # Get unsorted users (alters with user_class = 0) with the requisite in/out degree
    #users = list(User.objects.filter(user_class=0).filter(Q(in_degree__gte=REQUIRED_IN_DEGREE) | Q(out_degree__gte=REQUIRED_OUT_DEGREE)).values_list('user_id', flat=True))
    users = list(User.objects.filter(user_class=0).values_list('user_id', flat=True)) # TODO: Temporary while relos aren't created.
    length = len(users)
    print("Length of class-0 users to sort: {}".format(length))
    chunk_size = 100 # Max of 100
    index = 0
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
            print('Error with users: {}'.format(user_ids))
            index += chunk_size
            continue
        for user_data in user_list:
            u = User.objects.get(user_id=int(user_data.id_str))
            #Class the user as spam or 'alter'
            if check_spam_account(user_data):
                u.user_class = -1
            else:
                u.user_class = 1
            #If timezone is an issue:
            try:
                tz_aware = timezone.make_aware(user_data.created_at, timezone=pytz.utc)
            except (pytz.exceptions.AmbiguousTimeError, pytz.exceptions.NonExistentTimeError):
                # Adding an hour to avoid DST ambiguity errors.
                time_adjusted = user_data.created_at + timedelta(minutes=60)
                tz_aware = timezone.make_aware(time_adjusted, timezone=pytz.utc)
            #TODO: Need all these? Perhaps only for user_class >0? Merge with add_user section?
            u.created_at = tz_aware
            u.followers_count = user_data.followers_count
            u.friends_count = user_data.friends_count
            u.geo_enabled = user_data.geo_enabled
            u.location = user_data.location
            u.name = user_data.name
            u.screen_name = user_data.screen_name
            u.statuses_count = user_data.statuses_count
            try:
                u.save()
            except:
                print("Error saving user: {}".format(user_data.screen_name))
        index += chunk_size
    return


@shared_task(bind=True, soft_time_limit=20, time_limit=40, name='tasks.save_object', queue='save_object_q') #TODO: Handle this with rate limiting?
def save_twitter_object_task(self, tweet=None, user_class=0, save_entities=False, data_source=0, **kwargs):
    if tweet:
        try:
            tweet_obj = save_tweet(tweet, data_source, user_class, save_entities)
            if save_entities and DOWNLOAD_MEDIA and tweet_obj is not None:
                save_media_task.delay(tweet_obj, tweet)
        except Exception as e:
            print('Error saving tweet {}: {}'.format(tweet.id_str, e))
            pass
    else: # Saving user
        try:
            user_data = userdata.get_user(**kwargs)
            add_user(user_class=user_class, user_data=user_data, data_source=data_source)
        except Exception as e:
            print('Error adding user {}: {}'.format(user_data.id_str, e))
            pass
    return

#TODO: Move this back into methods, as issue has been fixed? Or refactor.
def download_media(tweet_data): # TODO: Fold into task ?
    event = Event.objects.all()[0].name
    media_type = ''
    media_url = []
    if tweet_data.source == 'Instagram':
        print('Saving data from source: {}'.format(tweet_data.source))
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
        print('Saving data from source: {}'.format(tweet_data.source))
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
            urlretrieve(m, directory + filename  + str(ext)) #TODO: Appears this is causing delay and not performing?
            saved_files.append(filename + str(ext))
            i += 1
    return(saved_files, media_type)

@shared_task(bind=True, soft_time_limit=300, time_limit=300, name='tasks.save_media', queue='save_media_q')
def save_media_task(self, tweet, tweet_data):
    filenames, type = download_media(tweet_data)
    # TODO: Decide how to link to tweet object - use a relation or three fields (base_name, type, count)
    if len(filenames) > 0:
        tweet.media_files = filenames
        tweet.media_files_type = type
        tweet.save()
    return


@shared_task(bind=True, name='tasks.compare_live_data_task', queue='save_object_q')
def compare_live_data_task(self):
    update_screen_names()
    check_deleted_tweets()
    return

#TODO: Move to methods and import?
#TODO: Currently appears buggy. Lists too long shortly after adding user, should be near-0
@shared_task(bind=True, name='tasks.update_user_relos_task', queue='save_object_q')
def update_user_relos_task(self):
    print('Runnning: Update Relo Task')
    print('WARNING: Running temporary (incomplete) implemention.')
    #TODO: Temporary Implementation:
    b = Event.objects.all()[0].kw_stream_start
    first_round = b + timedelta(days=3) # Focus on users from first 3 days of collection to manage volume
    #second_round = b + timedelta(days=7)
    users = User.objects.filter(user_class__gte=2, added_at__lt=first_round)
    #users = User.objects.filter(user_class__gte=2, added_at__gte=first_round, added_at__lt=second_round)

    print('Updating relo information for {} users.'.format(users.count()))

    c = 0
    for user in users:

        if c % 100 == 0:
            print('User {} of {}'.format(c, users.count()))
            #print('User ID: {}'.format(user.user_id))
        c += 1

        try:
            user_following_update = userdata.friends_ids(screen_name=user.screen_name)
        except:
            user_following_update = None
        if user_following_update:
            user.user_following_update = user_following_update
        try:
            user_followers_update = userdata.followers_ids(screen_name=user.screen_name)
        except:
            user_followers_update = None
        if user_followers_update:
            user.user_followers_update = user_followers_update
        user.user_network_update_observed_at = timezone.now()
        user.save()

    return

    users = User.objects.filter(user_class__gte=2).order_by('added_at')
    print('Updating relo information for {} users.'.format(users.count()))

    for user in users:
        #TODO: Possible add check: is new/dead links are over threshold, mark account as spam.
        # Particularly dead links, as new links may signify virality

        #Get true list of users followed by account
        user_following=userdata.friends_ids(user_id=user.user_id)
        if not user_following:
            #TODO: Handle suspended/deleted user here
            print('Suspected suspended account: {}'.format(user.user_id))
            continue
        #Get recorded list of users followed by account
        user_following_recorded = list(Relo.objects.filter(source_user=user).filter(end_observed_at=None).values_list('target_user__user_id', flat=True))

        new_friend_links = [a for a in user_following if (a not in user_following_recorded)]
        dead_friend_links = [a for a in user_following_recorded if (a not in user_following)]

        if len(new_friend_links):
            #print("New friend links for user: {}: {}".format(user.screen_name, new_friend_links))
            print("{} new friend links for user: {}".format(len(new_friend_links), user.screen_name))
        if len(dead_friend_links):
            #print("Dead friend links for user: {}: {}".format(user.screen_name, dead_friend_links))
            print("{} dead friend links for user: {}".format(len(dead_friend_links), user.screen_name))

        for target_user_id in dead_friend_links:
            for ob in Relo.objects.filter(source_user=user, target_user__user_id__contains=target_user_id).filter(end_observed_at=None):
                ob.end_observed_at = timezone.now()
                ob.save()
            tuser = User.objects.get(user_id=target_user_id)
            tuser.in_degree = tuser.in_degree - 1
            tuser.save()

            #Commented out to reduce DB calls:
            #user.out_degree -= 1
            #user.save()
        for target_user in new_friend_links:
            create_relo(user, target_user, outgoing=True)

        #Get true list of users following an account
        user_followers = userdata.followers_ids(user_id=user.user_id)
        if not user_followers:
            #TODO: Handle suspended/deleted user here
            continue
        #Get recorded list of users following an account
        user_followers_recorded = list(Relo.objects.filter(target_user=user).filter(end_observed_at=None).values_list('source_user__user_id', flat=True))

        new_follower_links = [a for a in user_followers if (a not in user_followers_recorded)]
        dead_follower_links = [a for a in user_followers_recorded if (a not in user_followers)]

        if len(new_follower_links):
            #print("New follower links for user: {}: {}".format(user.screen_name, new_follower_links))
            print("{} new follower links for user: {}".format(len(new_follower_links), user.screen_name))
        if len(dead_follower_links):
            #print("Dead follower links for user: {}: {}".format(user.screen_name, dead_follower_links))
            print("{} dead follower links for user: {}".format(len(dead_follower_links), user.screen_name))

        for source_user_id in dead_follower_links:
            for ob in Relo.objects.filter(target_user=user, source_user__user_id__contains=source_user_id).filter(end_observed_at=None):
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

    print('Updating relationship data complete.')
    return


@shared_task(bind=True, name='tasks.create_relo_network', queue='save_object_q')
def create_relo_network(self):
    #TODO: To be finished. Added to functions view.
    print('Create Network not yet implemented')
    return

    # Add to query - only return users with a follower/friend list array, and set to null afterward.
    users = User.objects.filter(user_class__gte=2)
    for u in users:

        user_following = u.user_following
        for target_user in user_following:
            create_relo(u, target_user, outgoing=True)

        user_followers = u.user_followers
        for source_user in user_followers:
            create_relo(u, source_user, outgoing=False)

        #TODO: remove id from array once added as a relo.
