import json
from tweepy import API, Cursor, OAuthHandler

from .config import CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKENS

#TODO iterate through access tokens
def get_api():
    auth = OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKENS[0][0], ACCESS_TOKENS[0][1])

    api = API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

    return api

#TODO: move this into per method, add limit checking
api = get_api()

# Returns all json data for screen_name/id
#TODO: Determine whether JSON is appropriate, or return all data instead
def get_user(**kwargs):
    print("Running function: get_user for user: {}".format(kwargs))
    userdata = api.get_user(**kwargs)
    #Remove duplicate data - return only JSON
    userdatadict = userdata.__dict__["_json"]

    return userdatadict

# Returns list of users (targets) followed by a screen_name/id, as a list of IDs.
def friends_ids(**kwargs):
    print("Running function: friends_ids for user: {}".format(kwargs))

    friends = Cursor(api.friends_ids, **kwargs).items()
    friends_list = [x for x in friends]

    return friends_list

# Returns list of user IDs following a screen_name/id
def followers_ids(**kwargs):
    print("Running function: followers_ids for user: {}".format(kwargs))

    followers = Cursor(api.followers_ids, **kwargs).items()
    followers_list = [x for x in followers]

    return followers_list
