import json
from django.core.exceptions import ObjectDoesNotExist

from tweepy import API, Cursor, OAuthHandler, RateLimitHandler

from streamcollect.models import AccessToken, ConsumerKey

api_global = None

def get_api():
    global api_global
    if api_global:
        return api_global

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
            print(t.access_key, e)
    #print('Token pool size: {}'.format(len(auth.tokens)))

    api_global = API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
    return api_global


# Returns all json data for screen_name/id
def get_user(**kwargs):
    api = get_api()
    userdata = api.get_user(**kwargs, include_entities=False)
    return userdata

# Returns user objects for list of screen_names/user_ids
def lookup_users(**kwargs):
    api = get_api()
    userdata = api.lookup_users(**kwargs, include_entities=False)
    return userdata

# Returns list of users (targets) followed by a screen_name/id, as a list of IDs.
def friends_ids(**kwargs):
    api = get_api()
    friends = Cursor(api.friends_ids, **kwargs, count=5000).items()
    friends_list = [x for x in friends]
    return friends_list

# Returns list of users followed by a screen_name/id, as a list of friend objects.
def friends_list(**kwargs):
    api = get_api()
    friends = Cursor(api.friends, **kwargs, count=200, include_entities=False, skip_status=True).items()
    friends_list = [x for x in friends]
    return friends_list

# Returns list of user IDs following a screen_name/id
def followers_ids(**kwargs):
    api = get_api()
    followers = Cursor(api.followers_ids, **kwargs, count=5000).items()
    followers_list = [x for x in followers]
    return followers_list

# Returns list of users following a screen_name/id
def followers_list(**kwargs):
    api = get_api()
    followers = Cursor(api.followers, **kwargs, count=200, include_entities=False, skip_status=True).items()
    followers_list = [x for x in followers]
    return followers_list

def user_timeline(**kwargs):
    api = get_api()
    # Pass the since_id into kwargs if needed
    # TODO: Consider keywords here - include_rts, etc. Decide on count value
    # TODO: This appears to return the same as non-extended text, truncated always
    # 'False'. Likely a tweepy bug. If fixed, adjust handling in save_tweet
    statuses = api.user_timeline(**kwargs, count=50, trim_user=True, tweet_mode='extended')
    #statuses = api.user_timeline(**kwargs, count=50, trim_user=True)
    return statuses
