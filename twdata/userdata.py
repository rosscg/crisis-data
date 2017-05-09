import json
import tweepy
#Import custom modules
from twdata import auth
#import auth #This line is used for package testing


# Returns all json data for username
#TODO: Determine whether JSON is appropriate, or return all data instead
#TODO: Remove useless parameters here
def usernamedata(username):
    print("Running function: usernamedata")
    api = auth.getapi()

    userdata = api.get_user(username)
    userdatadict = userdata.__dict__["_json"]

    return userdatadict

# Returns list of users (targets) followed by a username.
def userfollowing(username):
    print("Running function: userfollowing")
    api = auth.getapi()

    targetlist = []
    targets = tweepy.Cursor(api.friends_ids, screen_name=username).items()

    for userid in targets:
        targetlist.append(userid)

    return targetlist


# Returns list of users following a username.
# TODO: update to use IDs instead of names, remove followercount lines (followercount included in usernamedata)
def userfollowers(username):
    print("Running function: userfollowers")
    api = auth.getapi()

    #followerlist = []
    followers = tweepy.Cursor(api.followers_ids, screen_name=username).items()

    #for user in followers:
    #    followerlist.append(int(user.id_str))

    return followers
