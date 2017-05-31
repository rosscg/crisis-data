import json
import tweepy
#Import custom modules
from twdata import auth
#import auth #This line is used for package testing


# Returns all json data for username
#TODO: Determine whether JSON is appropriate, or return all data instead
#TODO: Remove useless parameters here
def usernamedata(username):
    print("Running function: usernamedata for user: {}".format(username))
    api = auth.getapi()

    userdata = api.get_user(username)
    userdatadict = userdata.__dict__["_json"]

    return userdatadict

# Returns list of users (targets) followed by a username, as a list of IDs.
def userfollowing(username):
    print("Running function: userfollowing for user: {}".format(username))
    api = auth.getapi()

    targetlist = []
    targets = tweepy.Cursor(api.friends_ids, screen_name=username).items()

    for userid in targets:
        targetlist.append(userid)

    return targetlist


# Returns list of user IDs following a username.
# TODO: update to use IDs instead of names, remove followercount lines (followercount included in usernamedata)
def userfollowers(username):
    print("Running function: userfollowers for user: {}".format(username))
    api = auth.getapi()

    followers = tweepy.Cursor(api.followers_ids, screen_name=username).items()

    return followers
