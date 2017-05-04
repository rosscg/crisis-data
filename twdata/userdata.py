import json
import tweepy
#Import custom modules
from twdata import auth


# Returns all json data for username
#TODO: Determine whether JSON is appropriate, or return all data instead
#TODO: Remove useless parameters here
def usernamedata(username):
    print("Running function: usernamedata")
    api = auth.getapi()

    userdata = api.get_user(username)
    userdatadict = userdata.__dict__["_json"]

    return userdatadict


# Returns list of users following a username.
def userfollowing(username):
    print("Running function: userfollowing")
    api = auth.getapi()

    followinglist = []

    followingcount = 0
    following = tweepy.Cursor(api.friends_ids, screen_name=username).items()

    for userid in following:
        print("user: {}".format(userid))
        followinglist.append(userid)
        followingcount += 1

    print("Username: {} follows {} users".format(username, followingcount))
    return followinglist


# Returns list of followed users.
# TODO: update to use IDs instead of names, remove followercount lines (followercount included in usernamedata)
def userfollowers(username):
    print("Running function: userfollowers")
    api = auth.getapi()

    followerlist = []

    followercount = 0
    followers = tweepy.Cursor(api.followers, screen_name=username).items()

    for user in followers:
        print("user:" + user.screen_name)
        followerlist.append(user.screen_name)
        followercount += 1

    print("Username: {} is followed by {} users".format(username, followercount))
    return followerlist
