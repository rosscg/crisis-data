from dateutil.parser import *
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Q
from celery.task.control import revoke
import tweepy

from .models import User, Relo, Tweet, CeleryTask, Keyword, AccessToken, ConsumerKey
from .forms import AddUserForm
from .tasks import save_twitter_object_task, update_user_relos_task, trim_spam_accounts
# Remove save_user_timeline:
from .methods import kill_celery_task, save_all_user_timelines, update_tracked_tags, add_users_from_mentions
from .config import REQUIRED_IN_DEGREE, REQUIRED_OUT_DEGREE, EXCLUDE_ISOLATED_NODES
from twdata import userdata
from twdata.tasks import twitter_stream_task
# Remove once in production (used by twitter_auth.html). Alternatively, this
# should load from a file in the parent, in the load_tokens method
#TODO: Currently causes an error on fresh db builds. Should be fine if Skeleton is renamed.
from .tokens import ACCESS_TOKENS, CONSUMER_SECRET, CONSUMER_KEY

def monitor_user(request):
    return render(request, 'streamcollect/monitor_user.html', {})

def list_users(request):
    users = User.objects.filter(user_class__gte=2)
    return render(request, 'streamcollect/list_users.html', {'users': users})

def view_network(request):
    return render(request, 'streamcollect/view_network.html')

def user_details(request, user_id):
    user = get_object_or_404(User, user_id=user_id)

    tweets = Tweet.objects.filter(author__user_id=user_id)
    #tweets = get_object_or_404(Tweet, author__user_id=user_id)
    return render(request, 'streamcollect/user_details.html', {'user': user, 'tweets': tweets})

def stream_status(request):
    keywords = Keyword.objects.all().values_list('keyword', flat=True).order_by('created_at')
    if not CeleryTask.objects.filter(task_name='stream_kw'):
        kw_stream_status = False
    else:
        kw_stream_status = True
    if not CeleryTask.objects.filter(task_name='stream_gps'):
        gps_stream_status = False
    else:
        gps_stream_status = True
    return render(request, 'streamcollect/stream_status.html', {'kw_stream_status': kw_stream_status, 'gps_stream_status': gps_stream_status, 'keywords': keywords})

def testbed(request):
    tasks = CeleryTask.objects.all().values_list('task_name', flat=True)
    return render(request, 'streamcollect/testbed.html', {'tasks': tasks})

def twitter_auth(request):
    tokens = AccessToken.objects.all()
    return render(request, 'streamcollect/twitter_auth.html', {'tokens': tokens})

def callback(request):
    try:
        ckey=ConsumerKey.objects.all()[:1].get()
    except ObjectDoesNotExist:
        print('Error! Failed to get Consumer Key from database.')
        return render(request, 'streamcollect/monitor_user.html')
    verifier = request.GET.get('oauth_verifier')
    auth = tweepy.OAuthHandler(ckey.consumer_key, ckey.consumer_secret)
    token = request.session.get('request_token', None)
    request.session.delete('request_token')
    auth.request_token = token
    tokens = AccessToken.objects.all()
    try:
        auth.get_access_token(verifier)
    except tweepy.TweepError:
        print('Error! Failed to get access token.')
        return render(request, 'streamcollect/twitter_auth.html', {'error': 'Failed to get access token','tokens': tokens})
    if not AccessToken.objects.filter(access_key=auth.access_token).exists():
        token = AccessToken(access_key=auth.access_token, access_secret=auth.access_token_secret, screen_name=auth.get_username())
        token.save()
    return render(request, 'streamcollect/twitter_auth.html', {'success': 'True', 'token': auth.access_token, 'tokens': tokens})

def submit(request):
    if "screen_name" in request.POST:
        #TODO: Add validation function here
        info = request.POST['info']
        if len(info) > 0:
            save_twitter_object_task.delay(user_class=2, screen_name=info)
        return redirect('monitor_user')
    elif "add_keyword" in request.POST:
        info = request.POST['info']
        if len(info) > 0:
            k = Keyword()
            k.keyword = info.lower()
            k.save()
        return redirect('monitor_user')
    elif "start_kw_stream" in request.POST:
        task = twitter_stream_task.delay()
        task_object = CeleryTask(celery_task_id = task.task_id, task_name='stream_kw')
        task_object.save()
        return redirect('stream_status')
    elif "start_gps_stream" in request.POST:
        #TODO: Store and upate gps coords in an event object
        #TODO: Starting/killing gps task doesn't appear to work. May just be queued in Redis
        gps = [-99.9590682, 26.5486063, -93.9790001, 30.3893434] # Corpus Christi, Texas
        task = twitter_stream_task.delay(gps)
        task_object = CeleryTask(celery_task_id = task.task_id, task_name='stream_gps')
        task_object.save()
        return redirect('stream_status')
    elif "stop_kw_stream" in request.POST:
        kill_celery_task('stream_kw')
        return redirect('stream_status')
    elif "stop_gps_stream" in request.POST:
        kill_celery_task('stream_gps')
        return redirect('stream_status')
    elif "trim_spam_accounts" in request.POST:
        task = trim_spam_accounts.delay()
        return redirect('testbed')
    elif "update_user_relos" in request.POST:
        task = update_user_relos_task.delay()
        return redirect('testbed')
    elif "delete_keywords" in request.POST:
        Keyword.objects.all().delete()
        return redirect('testbed')
    elif "terminate_tasks" in request.POST:
        for t in CeleryTask.objects.all():
            revoke(t.celery_task_id, terminate=True)
            t.delete()
        return redirect('testbed')
    elif "twitter_auth" in request.POST:
        try:
            ckey=ConsumerKey.objects.all()[:1].get()
        except ObjectDoesNotExist:
            print('Error! Failed to get Consumer Key from database.')
            return render(request, 'streamcollect/monitor_user.html')
        auth = tweepy.OAuthHandler(ckey.consumer_key, ckey.consumer_secret, 'http://127.0.0.1:8000/callback')
        try:
            redirect_url = auth.get_authorization_url()
            request.session['request_token'] = auth.request_token
        except tweepy.TweepError:
            print('Error! Failed to get request token.')
            return render(request, 'streamcollect/monitor_user.html')
        return redirect(redirect_url)
    #TODO: Remove after testing?
    elif "load_tokens" in request.POST:
        if not ConsumerKey.objects.filter(consumer_key=CONSUMER_KEY).exists():
            ckey = ConsumerKey(consumer_key=CONSUMER_KEY, consumer_secret=CONSUMER_SECRET)
            ckey.save()
        for n, k, s in ACCESS_TOKENS:
            if not AccessToken.objects.filter(access_key=k).exists():
                token = AccessToken(screen_name=n, access_key=k, access_secret=s)
                token.save()
        return redirect('twitter_auth')
    elif "export_tokens" in request.POST:
        try:
            ckey=ConsumerKey.objects.all()[:1].get()
        except ObjectDoesNotExist:
            print('Error! Failed to get Consumer Key from database.')
            return render(request, 'streamcollect/monitor_user.html')
        tokens = AccessToken.objects.all()
        f = open('tokens_export.py', 'w')
        f.write('CONSUMER_KEY = \'' + ckey.consumer_key + '\'\n')
        f.write('CONSUMER_SECRET = \'' + ckey.consumer_secret + '\'\n')
        f.write('ACCESS_TOKENS = (\n')
        for t in tokens:
            f.write('\t' + t.__str__() + ',\n')
        f.write(')')
        f.close
        return redirect('twitter_auth')
    #TODO: Remove:
    elif "user_timeline" in request.POST:
        save_all_user_timelines()
        #data = save_user_timeline(screen_name='QueensCollege')
        return redirect('testbed')
    elif "update_data" in request.POST:
        update_tracked_tags()
        add_users_from_mentions()
        return redirect('testbed')
    else:
        print("Unlabelled button pressed")
        return redirect('monitor_user')

#API returns users above a 'relevant in degree' threshold and the links between them
def network_data_API(request):
    print("Collecting network_data...")

    #All ego nodes, and alters with an in/out degree of X or greater.
    relevant_users = User.objects.filter(user_class__gte=1).filter(Q(in_degree__gte=REQUIRED_IN_DEGREE) | Q(out_degree__gte=REQUIRED_OUT_DEGREE) | Q(user_class__gte=2))

    #Get relationships which connect two 'relevant users'. This is slow. Could pre-generate?
    relevant_relos = Relo.objects.filter(target_user__in=relevant_users, source_user__in=relevant_users, end_observed_at=None)
    resultsrelo = [ob.as_json() for ob in relevant_relos]

    #Remove isolated nodes: TODO: May be too slow
    if EXCLUDE_ISOLATED_NODES:
        targets = list(relevant_relos.values_list('target_user', flat=True))
        sources = list(relevant_relos.values_list('source_user', flat=True))

        relo_node_list = targets + list(set(sources) - set(targets))

        resultsuser = [ob.as_json() for ob in relevant_users if ob.id in relo_node_list]
    else:
        resultsuser = [ob.as_json() for ob in relevant_users]

    data = {"nodes" : resultsuser, "links" : resultsrelo}
    jsondata = json.dumps(data)

    # Save to CSV for use in Gephi
    #csv = open('data_csv.csv','w')
    #for relo in relevant_relos:
    #    csv.write(relo.as_csv()+'\n')
    #csv.close()

    #TODO: HttpReponse vs Jsonresponse? Latter doesn't work with current d3
    return HttpResponse(jsondata)
