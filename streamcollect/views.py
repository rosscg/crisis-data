from dateutil.parser import *
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Q
from celery.task.control import revoke
import tweepy
import random

from django.utils import timezone

from .models import User, Relo, Tweet, DataCode, Coder, CeleryTask, Keyword, AccessToken, ConsumerKey, Event, GeoPoint
from .forms import EventForm, GPSForm
from .tasks import save_twitter_object_task, update_user_relos_task, save_user_timelines_task, trim_spam_accounts
from .methods import kill_celery_task, update_tracked_tags, add_users_from_mentions
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
    users = User.objects.filter(user_class__gte=2)[0:100]
    return render(request, 'streamcollect/list_users.html', {'users': users})


def view_network(request):
    return render(request, 'streamcollect/view_network.html')


def view_event(request):
    mid_point = None
    try:
        event = Event.objects.all()[0]
        if event.geopoint.all().count() == 2:
            mid_point = ((event.geopoint.all()[0].latitude + event.geopoint.all()[1].latitude) / 2 , (event.geopoint.all()[0].longitude + event.geopoint.all()[1].longitude) /2)
    except:
        event = None
    return render(request, 'streamcollect/view_event.html', {'event': event, 'mid_point': mid_point})


def edit_event(request): # Temp
    try:
        event = Event.objects.all()[0]
    except:
        event = None
    try:
        geo1 = GeoPoint.objects.all()[0]
    except:
        geo1 = None
    try:
        geo2 = GeoPoint.objects.all()[1]
    except:
        geo2 = None
    if request.method == "POST":
        form1 = EventForm(request.POST, instance=event)
        form2 = GPSForm(request.POST, instance=geo1, prefix='GeoPoint 1')
        form3 = GPSForm(request.POST, instance=geo2, prefix='GeoPoint 2')
        if form1.is_valid() and form2.is_valid() and form3.is_valid():
            form1.save()
            form2.save()
            form3.save()
        return redirect('view_event')
    else:
        form = EventForm(instance=event)
        form2 = GPSForm(instance=geo1, prefix='GeoPoint 1')
        form3 = GPSForm(instance=geo2, prefix='GeoPoint 2')
        return render(request, 'streamcollect/edit_event.html', {'forms': [form, form2, form3]})


def user_details(request, user_id):
    user = get_object_or_404(User, user_id=user_id)

    tweets = Tweet.objects.filter(author__user_id=user_id).order_by('created_at')
    #tweets = get_object_or_404(Tweet, author__user_id=user_id)
    return render(request, 'streamcollect/user_details.html', {'user': user, 'tweets': tweets})


def stream_status(request):
    keywords = Keyword.objects.all().values_list('keyword', flat=True).order_by('created_at')
    if not CeleryTask.objects.filter(task_name='stream_kw_high'):
        kw_stream_status = False
    else:
        kw_stream_status = True
    if not CeleryTask.objects.filter(task_name='stream_gps'):
        gps_stream_status = False
    else:
        gps_stream_status = True
    return render(request, 'streamcollect/stream_status.html', {'kw_stream_status': kw_stream_status, 'gps_stream_status': gps_stream_status, 'keywords': keywords})


def functions(request):
    tasks = CeleryTask.objects.all().values_list('task_name', flat=True)
    return render(request, 'streamcollect/functions.html', {'tasks': tasks})


def coding_interface(request, coder):
    if coder is '1':
        try:
            d = DataCode.objects.get(data_code_id=0)
        except:
            d = DataCode(data_code_id=0, name='To Be Coded')
            d.save()
        if DataCode.objects.get(data_code_id=0).tweets.all().count() is 0:
            tweet_all = Tweet.objects.filter(data_source__gt=0).filter(datacode__isnull=True) # Select un-coded Tweet from streams
            tweet_sample = tweet_all.order_by('?')[:10]                     #TODO: Scales very poorly, reconsider using random.sample to extract by row
            for i in tweet_sample:
                    new_coder = Coder(tweet=i, data_code=d)
                    new_coder.save()
        tweet_query = DataCode.objects.get(data_code_id=0).tweets.all()
        remaining = Tweet.objects.filter(data_source__gt=0).filter(~Q(datacode__data_code_id__gt=0)).count()
        count = tweet_query.count()
    else:
        tweet_query = Tweet.objects.filter(datacode__isnull=False).filter(~Q(coder__coder_id=coder)).filter(datacode__data_code_id__gt=0) # Select coded Tweet which hasn't been coded by the current coder.
        count = tweet_query.count()
        remaining = count
    if count > 0:
        rand = random.randint(0, (count-1))
        tweet = tweet_query[rand]
    else:
        tweet = None
    total_coded = Coder.objects.filter(coder_id=int(coder)).filter(data_code__data_code_id__gt=0).count() #Total coded by current coder
    codes = DataCode.objects.order_by('data_code_id')[1:] #Excludes 0 'to be coded' code
    return render(request, 'streamcollect/coding_interface.html', {'tweet': tweet, 'codes': codes, 'coder': coder, 'remaining': remaining, 'total_coded': total_coded})


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
    # TODO Remove - is no longer used ?
    if "screen_name" in request.POST:
        #TODO: Add validation function here
        info = request.POST['info']
        if len(info) > 0:
            save_twitter_object_task.delay(user_class=2, screen_name=info)
        return redirect('monitor_user')

    elif "add_keyword_low" in request.POST:
        info = request.POST['info']
        if len(info) > 0:
            k = Keyword()
            k.keyword = info.lower()
            k.created_at = timezone.now()
            k.priority = 1
            k.save()
        return redirect('monitor_user')

    elif "add_keyword_high" in request.POST:
        info = request.POST['info']
        if len(info) > 0:
            k = Keyword()
            k.keyword = info.lower()
            k.created_at = timezone.now()
            k.priority = 2
            k.save()
        return redirect('monitor_user')

    elif "add_data_code" in request.POST:
        code = request.POST['code']
        description = request.POST['description']
        d = list(DataCode.objects.values_list('data_code_id', flat=True))
        data_code_id = min([i for i in list(range(1,10)) if i not in d]) # Smallest ID not already in use
        if len(code) > 0:
            c = DataCode(name=code, description=description, data_code_id=data_code_id)
            c.save()
        return redirect('coding_interface', 0)

    elif "delete_data_code" in request.POST:
        data_code_id = request.POST['data_code_id']
        data_code = DataCode.objects.filter(data_code_id=data_code_id)
        data_code.delete()
        return redirect('coding_interface', 0)

    elif "start_kw_stream" in request.POST:
        try:
            event = Event.objects.all()[0]
        except:
            return redirect('view_event')
        if event.kw_stream_start is None or event.kw_stream_start > timezone.now():
            event.kw_stream_start = timezone.now()
            event.save()
        task_low = twitter_stream_task.delay(priority=1)
        task_high = twitter_stream_task.delay(priority=2)
        task_object = CeleryTask(celery_task_id = task_low.task_id, task_name='stream_kw_low')
        task_object.save()
        task_object = CeleryTask(celery_task_id = task_high.task_id, task_name='stream_kw_high')
        task_object.save()
        return redirect('stream_status')

    elif "start_gps_stream" in request.POST:
        try:
            event = Event.objects.all()[0]
        except:
            return redirect('view_event')
        if event.geopoint.all().count() == 2:
            gps = [event.geopoint.all()[0].longitude, event.geopoint.all()[0].latitude, event.geopoint.all()[1].longitude, event.geopoint.all()[1].latitude]
        elif event.geopoint.all().count() == 1:
            gps = [event.geopoint.all()[0].longitude, event.geopoint.all()[0].latitude]
        else: # No GPS coordinates
            return redirect('view_event')
        if event.gps_stream_start is None or event.gps_stream_start > timezone.now():
            event.gps_stream_start = timezone.now()
            event.save()
        task = twitter_stream_task.delay(gps)
        task_object = CeleryTask(celery_task_id = task.task_id, task_name='stream_gps')
        task_object.save()
        return redirect('stream_status')

    elif "stop_kw_stream" in request.POST:
        kill_celery_task('stream_kw_high')
        kill_celery_task('stream_kw_low')
        event = Event.objects.all()[0]
        if event.kw_stream_end is None or event.kw_stream_end < timezone.now():
            event.kw_stream_end = timezone.now()
            event.save()
        return redirect('stream_status')

    elif "stop_gps_stream" in request.POST:
        kill_celery_task('stream_gps')
        event = Event.objects.all()[0]
        if event.gps_stream_end is None or event.gps_stream_end < timezone.now():
            event.gps_stream_end = timezone.now()
            event.save()
        return redirect('stream_status')

    elif "trim_spam_accounts" in request.POST:
        task = trim_spam_accounts.delay()
        return redirect('functions')

    elif "update_user_relos" in request.POST:
        task = update_user_relos_task.delay()
        return redirect('functions')

    elif "delete_keywords" in request.POST:
        Keyword.objects.all().delete()
        return redirect('functions')

    elif "terminate_tasks" in request.POST:
        for t in CeleryTask.objects.all():
            revoke(t.celery_task_id, terminate=True)
            t.delete()
        return redirect('functions')

    elif "user_timeline" in request.POST:
        users = User.objects.filter(user_class__gte=2)
        save_user_timelines_task.delay(users)
        return redirect('functions')

    elif "update_data" in request.POST:
        update_tracked_tags()
        add_users_from_mentions()
        return redirect('functions')

    elif "export_data" in request.POST:
        tweets = Tweet.objects.filter(data_source__gte=1)
        i=0
        for tweet in tweets:
            i += 1
            txt = open('data_export/'+str(i)+'.txt','w')
            txt.write(tweet.text)
            txt.close()
        return redirect('functions')

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

    elif "assign_code" in request.POST:
        code_id = request.POST['assign_code']
        tweet_id = request.POST['tweet_id']
        coder_id = request.POST['coder']
        tweet = Tweet.objects.get(tweet_id=tweet_id)
        data_code = DataCode.objects.get(data_code_id=code_id)
        coder = Coder(tweet=tweet, data_code=data_code, coder_id=coder_id) #Add new code classification
        Coder.objects.filter(tweet=tweet).filter(data_code__data_code_id=0).delete() #Delete 'To Be Coded' classification
        coder.save()
        return redirect('/coding_interface/{}'.format(coder_id))

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
