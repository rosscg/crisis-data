import tweepy
import os

def getapi():
    # Reading token data from text filter. Splitlines() used to remove the newline tag.
    # TODO: Move the tokendata.txt file to a more appropriate folder. See note about where file is run from. (relative to the current process working directory)
    # TODO remove the print path line (and the import os)
    f = open('tokendata.txt')

    dir_path = os.path.dirname(os.path.realpath(f.name))
    print("Using authentication file: {}/{}".format(dir_path, f.name))

    lines = f.read().splitlines()

    ckey=lines[1]
    csecret=lines[2]
    atoken=lines[3]
    asecret=lines[4]

    auth = tweepy.OAuthHandler(ckey, csecret)
    auth.set_access_token(atoken, asecret)

    api = tweepy.API(auth)

    return api
