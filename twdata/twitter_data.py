import random
import time
from django.core.exceptions import ObjectDoesNotExist

from tweepy import Stream, OAuthHandler
from tweepy.streaming import StreamListener

from streamcollect.models import Keyword, AccessToken, ConsumerKey
#from .config import CONSUMER_KEY, CONSUMER_SECRET
from streamcollect.config import STREAM_REFRESH_RATE, REFRESH_STREAM, FRIENDS_THRESHOLD, FOLLOWERS_THRESHOLD, STATUSES_THRESHOLD, BOUNDING_BOX_WIDTH, BOUNDING_BOX_HEIGHT, STREAM_PROPORTION, IGNORED_KWS, IGNORED_SOURCES, IGNORE_RTS

from streamcollect.tasks import save_twitter_object_task
from streamcollect.methods import kill_celery_task

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

        # Exclude tweets with phrases from exclusion list.
        for kw in IGNORED_KWS:
            if kw in status.text.lower():
                return
            for tag in status.entities.get('hashtags'):
                if kw in tag.get('text'):
                    return

        # Exclude sources from exclusion list.
        for source in IGNORED_SOURCES:
            if source in status.source:
                return

        # TODO: Remove or comment out, consider adding IGNORED_USERS to config as above.
        if status.author.screen_name[0:4] == 'tmj_': # Excluding TMJ spam (USA)
            return

        # These values are checked here and at the user_save function.
        if status.user.followers_count > FOLLOWERS_THRESHOLD:
            return
        if status.user.friends_count > FRIENDS_THRESHOLD:
            return
        if status.user.statuses_count > STATUSES_THRESHOLD:
            return

        # Ignore if retweet.
        if IGNORE_RTS:
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
                    return  # Returns if Tweet is streamed but doesn't match any keywords.
                            # For example, stream will return Tweets which quote Tweets containing the keyword.
                            # We are therefore currently discarding these. TODO: Could choose to handle.
                r = random.random()
                if r > STREAM_PROPORTION:
                    return
        else: # GPS stream
            data_source = 3 # data_source = GPS stream
            if status.coordinates is None:      # Tweets are sometimes allocated a 'Place' by Twitter which will
                                                # return in GPS stream (as the place's coords) despite not having specific coordsself.
                data_source = 4
                #return
            else:   #TODO: This shouldn't happen if bounding box is working correctly
                coords = status.coordinates.get('coordinates')
                ##print('Coordinates: {}'.format(coords))
                if self.gps_bool:
                    if not self.data[0] < coords[0] < self.data[2]:
                        print("ERROR Coordinates outside longitude")
                        return
                    if not self.data[1] < coords[1] < self.data[3]:
                        print("ERROR Coordinates outside latitude")
                        return

        print(status.text)
        save_twitter_object_task.delay(tweet=status, user_class=2, save_entities=True, data_source=data_source, id=int(status.user.id_str))
        return

    def on_error(self, status):
        print("Error detected>>>>>>>>>>>>>>>>>>>>>>>>>>>> {}".format(status))

    def on_timeout(self):
        print("Connection timed out, ")

def twitter_stream(gps=False, priority=1):

    try:
        ckey=ConsumerKey.objects.all()[:1].get()
    except ObjectDoesNotExist:
        print('Error! Failed to get Consumer Key from database.')
        return
    try:
        if priority == 1:
            access_token=AccessToken.objects.all()[:1].get()
        elif gps:
            access_token=AccessToken.objects.all()[1:2].get()
        else:
            access_token=AccessToken.objects.all()[2:3].get()
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
        elif len(gps) is 2: # TODO: Consider putting this into views, always pass 4 values
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
            if priority == 2:
                kill_celery_task('stream_kw_high')
            elif priority == 1:
                kill_celery_task('stream_kw_low')
            return
    #twitterStream = Stream(auth, stream_listener(gps, data))
    twitterStream = Stream(auth, stream_listener(gps, data), tweet_mode='extended') #TODO: Test, Adjust on both lines. Test for retweets. Adjust how RTs are hard-coded to handle for IGNORE_RTS

    if gps:
        twitterStream.filter(locations=data, async=False)
    elif REFRESH_STREAM:            # Refresh stream to read in new keywords
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
                #twitterStream = Stream(auth, stream_listener(False, data))
                twitterStream = Stream(auth, stream_listener(False, data), tweet_mode='extended')
            print("Running new stream (with refresh)...")
            twitterStream.filter(track=data, async=False)
            time.sleep(STREAM_REFRESH_RATE)
    else:
        print('Running stream priority: {} with keywords: {}'.format(priority, data))
        twitterStream.filter(track=data, async=False)


#TODO: Fold this back into methods?
def get_keywords(priority):
    global keywords_low_priority_global
    global keywords_high_priority_global
    #keywords_global = list(Keyword.objects.all().values_list('keyword', flat=True).order_by('created_at'))
    keywords_high_priority_global = list(Keyword.objects.filter(priority=2).values_list('keyword', flat=True).order_by('created_at'))
    keywords_low_priority_global = list(Keyword.objects.filter(priority=1).values_list('keyword', flat=True).order_by('created_at'))
    #keywords_global = Keyword.objects.all().values_list('keyword', flat=True).order_by('created_at')
    if priority == 1:
        return keywords_low_priority_global
    elif priority == 2:
        return keywords_high_priority_global
    else:
        print('Error with priority value: {}'.format(priority))
