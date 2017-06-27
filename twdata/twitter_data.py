import time

from tweepy import Stream, OAuthHandler
from tweepy.streaming import StreamListener

#from streamcollect.models import User, Relo
#from .userdata import get_api

from streamcollect.models import Keyword, AccessToken
from .config import CONSUMER_KEY, CONSUMER_SECRET
from streamcollect.config import STREAM_REFRESH_RATE, FRIENDS_THRESHOLD, FOLLOWERS_THRESHOLD, STATUSES_THRESHOLD

from streamcollect.tasks import add_user_task
from streamcollect.methods import kill_celery_task

class stream_listener(StreamListener):

    def __init__(self, gps_bool, data):
        self.api = None
        self.gps_bool = gps_bool
        self.data = data

    def on_status(self, status):
        if self.gps_bool:
            if status.coordinates is None:
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

        print(status.text)
        # May have to dump from JSON? coords = json.dumps(coords)
        if status.coordinates is not None:
            coords = status.coordinates.get('coordinates')
            print(coords)
            if self.gps_bool:
                if not self.data[0] < coords[0] < self.data[2]:
                    print("ERROR Coordinates outside longitude")
                if not self.data[1] < coords[1] < self.data[3]:
                    print("ERROR Coordinates outside latitude")

        print("Adding user: {} ...".format(int(status.user.id_str)))
        add_user_task.delay(user_class=2, id = int(status.user.id_str))
        return

    def on_error(self, status):
        print("Error detected>>>>>>>>>>>>>>>>>>>>>>>>>>>> ")
        print(status)

    def on_timeout(self):
        print("Connection timed out, ")

def twitter_stream(gps=False):

    #TODO: Only using first token. Needs a try/exception block.
    access_token=AccessToken.objects.all()[:1].get()

    #TODO: Merge this with other auth in userdata.py
    auth = OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(access_token.access_key, access_token.access_secret)

    if gps:
        print("Coords detected.")
        if len(gps) is 4:
            bounding_box = gps
        elif len(gps) is 2:
            bounding_box = [gps[0]-.4, gps[1]-0.25, gps[0]+.4, gps[1]+0.25,]
        else:
            print("Error: no gps coordinates passed to gps_stream: {}".format(gps))
            kill_celery_task('stream_gps')
            return
        print("Using bounding box: {}".format(bounding_box))
        data = gps
    else:
        data = get_keywords()
        if len(data) == 0:
            print("Error: no keywords found.")
            kill_celery_task('stream_kw')
            return

    twitterStream = Stream(auth, stream_listener(gps, data))

    if gps:
        twitterStream.filter(locations=data, async=True)
    else:
        while True:
            if twitterStream.running:
                twitterStream.disconnect()
                print("Deleting old stream...")
                del twitterStream
                data = get_keywords()
                if len(data) == 0:
                    print("Error: no keywords found.")
                    return
                twitterStream = Stream(auth, stream_listener(False, data))
            print("Running new stream...")
            twitterStream.filter(track=data, async=True)
            time.sleep(STREAM_REFRESH_RATE)

#TODO: Fold this back into methods?
def get_keywords():
    keywords = Keyword.objects.all().values_list('keyword', flat=True).order_by('created_at')
    return keywords
