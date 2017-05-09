import tweepy
import os

def getapi():
    # Reading token data from text filter. Splitlines() used to remove the newline tag.
    # TODO remove the print path line (and the import os)
    # TODO add catch for file open failure
    f = open('tokendata.txt')

    dir_path = os.path.dirname(os.path.realpath(f.name))
    #print("Using authentication file: {}/{}".format(dir_path, f.name))

    lines = f.read().splitlines()

    ckey=lines[1]
    csecret=lines[2]
    atoken=lines[3]
    asecret=lines[4]

    auth = tweepy.OAuthHandler(ckey, csecret)
    auth.set_access_token(atoken, asecret)

    api = tweepy.API(auth, wait_on_rate_limit= True, wait_on_rate_limit_notify=True)

    return api
