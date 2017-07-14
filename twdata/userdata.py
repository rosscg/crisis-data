import json
from django.core.exceptions import ObjectDoesNotExist

from tweepy import API, Cursor, OAuthHandler, RateLimitHandler

from streamcollect.models import AccessToken, ConsumerKey

def get_api():
    try:
        ckey=ConsumerKey.objects.all()[:1].get()
        access_tokens=AccessToken.objects.all()
    except ObjectDoesNotExist:
        print('Error! Failed to get Consumer or Access Key from database.')
        return

    auth = RateLimitHandler(ckey.consumer_key, ckey.consumer_secret)

    for t in access_tokens:
        try:
            auth.add_access_token(t.access_key, t.access_secret)
        except Exception as e:
            print(key, e)

    print('Token pool size: {}'.format(len(auth.tokens)))

    #auth.set_access_token(access_token.access_key, access_token.access_secret)
    api = API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
    return api


#TODO: move this into per method, add limit checking. Causes errors when building as new project
api = get_api()

# Returns all json data for screen_name/id
def get_user(**kwargs):
    print("Running function: get_user for user: {}".format(kwargs))
    userdata = api.get_user(**kwargs, include_entities=False)
    return userdata

# Returns user objects for list of screen_names/user_ids
def lookup_users(**kwargs):
    print("Running function: lookup_users.")
    userdata = api.lookup_users(**kwargs, include_entities=False)
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
