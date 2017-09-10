import random
import time
from django.core.exceptions import ObjectDoesNotExist

from tweepy import Stream, OAuthHandler
from tweepy.streaming import StreamListener

from streamcollect.models import Keyword, AccessToken, ConsumerKey
#from .config import CONSUMER_KEY, CONSUMER_SECRET
from streamcollect.config import STREAM_REFRESH_RATE, REFRESH_STREAM, FRIENDS_THRESHOLD, FOLLOWERS_THRESHOLD, STATUSES_THRESHOLD, BOUNDING_BOX_WIDTH, BOUNDING_BOX_HEIGHT, STREAM_PROPORTION

from streamcollect.tasks import save_twitter_object_task
from streamcollect.methods import kill_celery_task, save_tweet

keywords_high_priority_global = None
keywords_low_priority_global = None

class stream_listener(StreamListener):

    def __init__(self, gps_bool, data):
        self.api = None
        self.gps_bool = gps_bool
        self.data = data

    def on_status(self, status):

        # Check that keywords exist (Twitter doesn't handle phrases with spaces)
        #TODO: This currently excludes replies/links if the tag is in the external
        # entity. Decide whether to handle.
        # Status.truncated doesn't appear to be True when user reposts from Instagram or Facebook
        if status.truncated:
            text=status.extended_tweet.get('full_text')
        else:
            text=status.text

        # Exclude tweets with 'pray'.
        if 'pray' in status.text.lower():
            return
        for tag in status.entities.get('hashtags'):
            if 'pray' in tag.get('text'):
                return

        if status.user.followers_count > FOLLOWERS_THRESHOLD:
            return
        if status.user.friends_count > FRIENDS_THRESHOLD:
            return
        if status.user.statuses_count > STATUSES_THRESHOLD:
            return

        # Return if retweet.
        try:
            status.retweeted_status
        except AttributeError:
            pass
        else:
            return

        if not self.gps_bool:
            data_source = 2 # data_source = High-priority keyword stream
            global keywords_high_priority_global
            global keywords_low_priority_global
            # Process smaller proportion of Tweets
            if not any(x in text.lower() for x in keywords_high_priority_global):
                data_source = 1 # data_source = Low-priority keyword stream
                if not any(x in text.lower() for x in keywords_low_priority_global):
                    return
                r = random.random()
                if r > STREAM_PROPORTION:
                    return
        else: # GPS stream
            data_source = 3# data_source = GPS stream
            if status.coordinates is None:
                return

        # May have to dump from JSON? coords = json.dumps(coords)
        if status.coordinates is not None:
            coords = status.coordinates.get('coordinates')
            #print('Coordinates: {}'.format(coords))
            if self.gps_bool:
                # TODO: Remove or comment out:
                if status.author.screen_name[0:4] == 'tmj_': # Excluding TMJ spam (USA)
                    return
                if not self.data[0] < coords[0] < self.data[2]:
                    #print("ERROR Coordinates outside longitude")
                    return
                if not self.data[1] < coords[1] < self.data[3]:
                    #print("ERROR Coordinates outside latitude")
                    return

        print(status.text)

        save_twitter_object_task.delay(tweet=status, user_class=2, save_entities=True, data_source=data_source, id=int(status.user.id_str))
        return

    def on_error(self, status):
        print("Error detected>>>>>>>>>>>>>>>>>>>>>>>>>>>> {}".format(status))

    def on_timeout(self):
        print("Connection timed out, ")

def twitter_stream(gps=False, priority=0):

    try:
        ckey=ConsumerKey.objects.all()[:1].get()
    except ObjectDoesNotExist:
        print('Error! Failed to get Consumer Key from database.')
        return
    try:
        access_token=AccessToken.objects.all()[:1].get()
    except ObjectDoesNotExist:
        print('Error! Failed to get Access Key from database.')
        return

    #TODO: Merge this with other auth in userdata.py
    auth = OAuthHandler(ckey.consumer_key, ckey.consumer_secret)
    auth.set_access_token(access_token.access_key, access_token.access_secret)

    if gps:
        print("Coords detected.")
        if len(gps) is 4:
            bounding_box = gps
        elif len(gps) is 2:
            bounding_box = [gps[0]-(BOUNDING_BOX_WIDTH/2), gps[1]-(BOUNDING_BOX_HEIGHT/2), gps[0]+(BOUNDING_BOX_WIDTH/2), gps[1]+(BOUNDING_BOX_HEIGHT/2)]
        else:
            print("Error: no gps coordinates passed to gps_stream: {}".format(gps))
            kill_celery_task('stream_gps')
            return
        print("Using bounding box: {}".format(bounding_box))
        data = bounding_box
    else:
        data = get_keywords(priority)
        if len(data) == 0:
            print("Error: no keywords found.")
            kill_celery_task('stream_kw')
            return
    print('Running priority: {} with keywords: {}'.format(priority, data))
    twitterStream = Stream(auth, stream_listener(gps, data))

    if gps:
        twitterStream.filter(locations=data, async=False)
    elif REFRESH_STREAM:
        #TODO: Currently returns replies where the original message included the phrase. Decide whether to keep. Also quoted tweets.
        #EG: https://twitter.com/HalfStrungHarp/status/887335974539317249
        while True:
            #Periodically re-run stream to get updated set of keywords.
            if twitterStream.running:
                twitterStream.disconnect()
                print("Deleting old stream...")
                del twitterStream
                data = get_keywords(priority)
                if len(data) == 0:
                    print("Error: no keywords found.")
                    kill_celery_task('stream_kw')
                    return
                twitterStream = Stream(auth, stream_listener(False, data))
            print("Running new stream (with refresh)...")
            twitterStream.filter(track=data, async=False)
            time.sleep(STREAM_REFRESH_RATE)
    else:
        print("Running new stream...")
        twitterStream.filter(track=data, async=False)


#TODO: Fold this back into methods?
def get_keywords(priority):
    global keywords_low_priority_global
    global keywords_high_priority_global
    #keywords_global = list(Keyword.objects.all().values_list('keyword', flat=True).order_by('created_at'))
    keywords_high_priority_global = list(Keyword.objects.filter(priority=1).values_list('keyword', flat=True).order_by('created_at'))
    keywords_low_priority_global = list(Keyword.objects.filter(priority=0).values_list('keyword', flat=True).order_by('created_at'))
    #keywords_global = Keyword.objects.all().values_list('keyword', flat=True).order_by('created_at')
    if priority == 0:
        return keywords_low_priority_global
    else:
        return keywords_high_priority_global
