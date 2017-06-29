import json
from django.core.exceptions import ObjectDoesNotExist

from tweepy import API, Cursor, OAuthHandler, RateLimitHandler

from streamcollect.models import AccessToken, ConsumerKey

#TODO iterate through access tokens
def get_api():
    #TODO: Only using first token. Need to implement multiple tokens
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

def get_oauth():
    try:
        ckey=ConsumerKey.objects.all()[:1].get()
    except ObjectDoesNotExist:
        print('Error! Failed to get Consumer Key from database.')
        return

    auth = tweepy.OAuthHandler(ckey.consumer_key, ckey.consumer_secret, 'http://127.0.0.1:8000')
    try:
        redirect_url = auth.get_authorization_url()
    except tweepy.TweepError:
        print('Error! Failed to get request token.')
    session.set('request_token', auth.request_token)

    verifier = request.GET.get('oauth_verifier')

    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    token = session.get('request_token')
    session.delete('request_token')
    auth.request_token = token

    try:
        auth.get_access_token(verifier)
    except tweepy.TweepError:
        print('Error! Failed to get access token.')

    #auth.access_token
    #auth.access_token_secret
    return


#TODO: move this into per method, add limit checking
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
