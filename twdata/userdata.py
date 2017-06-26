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
def get_user(**kwargs):
    print("Running function: get_user for user: {}".format(kwargs))
    userdata = api.get_user(**kwargs, include_entities=False)
    return userdata

# Returns list of users (targets) followed by a screen_name/id, as a list of IDs.
def friends_ids(**kwargs):
    print("Running function: friends_ids for user: {}".format(kwargs))
    friends = Cursor(api.friends_ids, **kwargs, count=5000).items()
    friends_list = [x for x in friends]
    return friends_list

# Returns list of users followed by a screen_name/id, as a list of friend objects.
def friends_list(**kwargs):
    print("Running function: friends_list for user: {}".format(kwargs))
    friends = Cursor(api.friends, **kwargs, count=200, include_entities=False, skip_status=True).items()
    friends_list = [x for x in friends]
    return friends_list

# Returns list of user IDs following a screen_name/id
def followers_ids(**kwargs):
    print("Running function: followers_ids for user: {}".format(kwargs))
    followers = Cursor(api.followers_ids, **kwargs, count=5000).items()
    followers_list = [x for x in followers]
    return followers_list

# Returns list of users following a screen_name/id
def followers_list(**kwargs):
    print("Running function: followers_list for user: {}".format(kwargs))
    followers = Cursor(api.followers, **kwargs, count=200, include_entities=False, skip_status=True).items()
    followers_list = [x for x in followers]
    return followers_list
