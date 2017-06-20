import time

from tweepy import Stream, OAuthHandler
from tweepy.streaming import StreamListener

#from streamcollect.models import User, Relo
#from .userdata import get_api

from .config import CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKENS

from streamcollect.tasks import add_user_task

class stream_listener(StreamListener):

    def __init__(self, gps_bool, data):
        self.api = None
        self.gps_bool = gps_bool
        self.data = data

    def on_status(self, status):
        if self.gps_bool:
            if status.coordinates is None:
                return
        #TODO: Unify these values with checks in add_user_task
        if status.user.followers_count > 2000:
            return
        if status.user.friends_count > 2000:
            return
        if status.user.statuses_count > 10000:
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
        add_user_task.delay(id = int(status.user.id_str))
        return

    def on_error(self, status):
        print("Error detected>>>>>>>>>>>>>>>>>>>>>>>>>>>> ")
        print(status)

    def on_timeout(self):
        print("Connection timed out, ")

def twitter_stream(gps=False):
    #TODO: Merge this with other auth in userdata.py
    auth = OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKENS[0][0], ACCESS_TOKENS[0][1])

    if gps:
        print("Coords detected.")
        if len(gps) is 4:
            bounding_box = gps
        elif len(gps) is 2:
            bounding_box = [gps[0]-.4, gps[1]-0.25, gps[0]+.4, gps[1]+0.25,]
        else:
            print("Error: no gps coordinates passed to gps_stream: {}".format(gps))
            return
        print("Using bounding box: {}".format(bounding_box))
        data = gps
    else:
        #TODO: Implement this
        data = get_keywords()

    twitterStream = Stream(auth, stream_listener(gps, data))

    if gps:
        twitterStream.filter(locations=data, async=True)
    else:
        while True:
            if twitterStream.running:
                twitterStream.disconnect()
                print("Deleting old stream...")
                del twitterStream
                #TODO: Implement this
                data = get_keywords()
                twitterStream = Stream(auth, stream_listener(False, data))
            print("Running new stream...")
            twitterStream.filter(track=data, async=True)
            time.sleep(600)
    #TODO: How to kill the stream without shutting down all workers?

#TODO: Implement this
def get_keywords():
    return ["Oxford"]
