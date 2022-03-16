from dateutil.parser import *
import json
from django.core.serializers.json import DjangoJSONEncoder

from django.shortcuts import render, get_object_or_404, redirect
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Q, Count
from django.db import IntegrityError

from celery.task.control import revoke
from celery.task.control import inspect
import tweepy
import random

import csv # for tweetData, userData.csv generation

# from twdata import userdata #TODO: Is this used?
from twdata.tasks import twitter_stream_task

from .models import (
    User, Relo, Tweet, DataCodeDimension, DataCode, Coding, Keyword,
    AccessToken, ConsumerKey, Event, GeoPoint, Hashtag, Url, Mention
    )
from .forms import EventForm, GPSForm
from .tasks import (
    create_relos_from_list_task,
    compare_live_data_task,
    save_twitter_object_task,
    save_user_timelines_task,
    trim_spam_accounts,
    update_user_relos_task
    )
from .methods import update_tracked_tags, add_users_from_mentions #, check_spam_account
from .contingency_matrix_funcs import calculate_agreement_coefs
from .networks import create_gephi_file
from .calculate_metrics import (
    calculate_user_graph_metrics,
    calculate_user_stream_metrics
    )
from .config import (
    EXCLUDE_ISOLATED_NODES,
    MAX_MAP_PINS,
    REQUIRED_IN_DEGREE,
    REQUIRED_OUT_DEGREE
    )
# Remove once in production (used by twitter_auth.html). Alternatively, this
# should load from a file in the parent, in the load_tokens method
#TODO: Currently causes an error on fresh db builds. Should be fine if Skeleton is renamed.
from .tokens import ACCESS_TOKENS, CONSUMER_SECRET, CONSUMER_KEY, MAPBOX_PK


def monitor_event(request):
    # List of data_sources chosen to be displayed
    selected_data_sources = request.session.get('active_data_sources', [])
    print('selected_data_sources: {}'.format(selected_data_sources))
     # Tweet with coordinates, or associated Place coordinates (for data_source=4):
    data_query = Tweet.objects.filter(
                    data_source__in=selected_data_sources).filter(
                    Q(coordinates_lat__isnull=False) | Q(data_source=4)).filter(
                    Q(quoted_by__isnull=True) & Q(replied_by__isnull=True))

    sample = min(data_query.count(), MAX_MAP_PINS)
    # TODO: order_by(?) is slow ? # order_by('?') is random
    tweets_list = [ obj.as_dict() for obj in data_query.order_by('?')[:sample] ]
    tweets = json.dumps(tweets_list, cls=DjangoJSONEncoder)
    mid_point = None
    bounding_box = None
    try:
        event = Event.objects.all()[0]
        if event.geopoint.all().count() == 2:
            geo_1 = event.geopoint.all()[0]
            geo_2 = event.geopoint.all()[1]
            mid_point = [(geo_1.latitude + geo_2.latitude) / 2 , (geo_1.longitude + geo_2.longitude) /2]
            bounding_box = [geo_1.latitude, geo_1.longitude, geo_2.latitude, geo_2.longitude]
        elif event.geopoint.all().count() > 0:
            geo_1 = event.geopoint.all()[0]
            mid_point = [geo_1.latitude, geo_1.longitude]
    except:
        event = None
    return render(request, 'streamcollect/monitor_event.html',
                            {'tweets': tweets,
                             'mid_point': json.dumps(mid_point),
                             'bounding_box': json.dumps(bounding_box),
                             'mapbox_pk': json.dumps(MAPBOX_PK),
                             'selected_data_sources': selected_data_sources})


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
            mid_point = ((event.geopoint.all()[0].latitude + event.geopoint.all()[1].latitude) / 2 ,
                         (event.geopoint.all()[0].longitude + event.geopoint.all()[1].longitude) / 2)
    except:
        event = Event.objects.create(name="UntitledEvent")
    return render(request, 'streamcollect/view_event.html', {'event': event, 'mid_point': mid_point})


def edit_event(request): # Temp, needs validation & better interface.
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
        return render(request, 'streamcollect/edit_event.html',
                                {'forms': [form, form2, form3],
                                'mapbox_pk': json.dumps(MAPBOX_PK) })


def user_details(request, user_id):
    user = get_object_or_404(User, user_id=user_id)
    tweets = Tweet.objects.filter(author__user_id=user_id).order_by('created_at')
    return render(request, 'streamcollect/user_details.html', {'user': user, 'tweets': tweets})


def user_feed(request, user_id):
    user = get_object_or_404(User, user_id=user_id)
    tweets = Tweet.objects.filter(author__user_id=user_id).order_by('created_at')
    #Exclude Retweets which are captured when saving user feed.
    #tweets = Tweet.objects.filter(author__user_id=user_id).exclude(text__startswith="RT @").order_by('created_at')
    return render(request, 'streamcollect/user_feed.html', {'user': user, 'tweets': tweets})


def stream_status(request):
    keywords = Keyword.objects.all().values_list('keyword', flat=True).order_by('created_at')

    kw_stream_status = False
    gps_stream_status = False

    #TODO: catch exception here for when workers aren't running (also in functions tab)
    try:
        ts = inspect(['celery@stream_worker']).active().get('celery@stream_worker')
    except:
        ts = []
    for t in ts:
        task_id = t.get('id')
        if 'priority' in t['kwargs']:
            kw_stream_status = True
        elif 'priority' not in t['kwargs']:
            gps_stream_status = True

    return render(request, 'streamcollect/stream_status.html',
                            {'kw_stream_status': kw_stream_status,
                            'gps_stream_status': gps_stream_status,
                            'keywords': keywords})


def functions(request):
    try:
        tasks = inspect(['celery@stream_worker']).active().get('celery@stream_worker') + inspect(['celery@object_worker']).active().get('celery@object_worker') + inspect(['celery@object_worker']).reserved().get('celery@object_worker')
    except:
        tasks = []
    tasks = [d['name'] for d in tasks]
    return render(request, 'streamcollect/functions.html', {'tasks': tasks})


def coding_dash(request):
    coding_subject = request.session.get('coding_subject', None)
    active_coding_dimension = request.session.get('active_coding_dimension', None)
    active_coder = request.session.get('active_coder', None)

    if coding_subject is None:
        request.session['coding_subject'] = 'tweet'
        coding_subject = 'tweet'

    if active_coder is None:
        request.session['active_coder'] = 1
        active_coder = 1

    dimensions = DataCodeDimension.objects.filter(coding_subject=coding_subject)
    if active_coding_dimension not in dimensions.values_list('id', flat=True) or active_coding_dimension is None:
        if dimensions.count() > 0:
            active_coding_dimension = dimensions.order_by('id')[0].id
        else:
            active_coding_dimension = None
        request.session['active_coding_dimension'] = active_coding_dimension

    return render(request, 'streamcollect/coding_dash.html', {'dimensions': dimensions, 'active_coding_dimension': active_coding_dimension, 'active_coder': active_coder, 'coding_subject': coding_subject})


def coding_interface(request):
    active_coder = request.session.get('active_coder', None)
    active_coding_dimension = request.session.get('active_coding_dimension', None)
    coding_subject = request.session.get('coding_subject', None)

    if active_coder is None:
        return redirect('coding_dash')
    if active_coder == 1:
        try:
            d = DataCode.objects.get(data_code_id=0)
        except:
            d = DataCode(data_code_id=0, name='To Be Coded')
            d.save()

        # TODO: The below blocks aim to select data which has been coded in other dimensions already,
        # however it does not prioritise data which has been coded in two dimensions, it samples
        # randomly from data which has been coded in *at least* one dimension. This isn't ideal at scale.
        if coding_subject == 'tweet':
            # Look for tweets coded in another dimension already:
            data_coded_in_other_dimension = Tweet.objects.filter(data_source__gt=0).filter(datacode__isnull=False).filter(~Q(datacode__dimension_id=active_coding_dimension)).filter(datacode__data_code_id__gt=0)
            data_to_be_coded = DataCode.objects.get(data_code_id=0).tweets.all() # This currently ignores dimension, but shouldn't impact functionality.
            data_cross_coded = Tweet.objects.filter(data_source__gt=0, author__datacode__data_code_id__gt=0, datacode__isnull=True) # Uncoded tweets which have authors already coded.
            data_cross_coded_queued = Tweet.objects.filter(data_source__gt=0, author__datacode__data_code_id=0, datacode__isnull=True) # Uncoded tweets which have authors queued for coding.
            data_all = Tweet.objects.filter(data_source__gt=0, datacode__isnull=True) # All uncoded Tweets
        else: # coding_subject is 'user'
            data_coded_in_other_dimension = User.objects.filter(user_class__gt=0).filter(datacode__isnull=False).filter(~Q(datacode__dimension_id=active_coding_dimension)).filter(datacode__data_code_id__gt=0)
            data_to_be_coded = DataCode.objects.get(data_code_id=0).users.all() # This currently ignores dimension, but shouldn't impact functionality.
            data_cross_coded = User.objects.filter(user_class__gt=0, tweet__datacode__data_code_id__gt=0, datacode__isnull=True) # Uncoded users which have tweets already coded.
            data_cross_coded_queued = User.objects.filter(user_class__gt=0, tweet__datacode__data_code_id=0, datacode__isnull=True) # Uncoded users whose tweets are queued for coding.
            data_all = User.objects.filter(user_class__gt=0, datacode__isnull=True) # All uncoded users

        if data_coded_in_other_dimension.count() == 0: # Check if data has been coded in other dimensions but not current dimension.
            if data_to_be_coded.count() == 0: # Check if there are data marked as 'To Be Coded', and create if not.
                #TODO Handle out of index below:::::
                batch_size = 10
                print("Fetching new batch of un-coded..")
                if data_cross_coded.count() > 0:
                    data_all = data_cross_coded
                elif data_cross_coded_queued.count() > 0:
                    data_all = data_cross_coded_queued
                if data_all.count() >= batch_size:
                    data_sample = data_all.order_by('?')[:batch_size] # TODO: Scales very poorly, reconsider using random.sample to extract by row
                else:
                    data_sample = data_all.order_by('?')[:data_all.count()]
                for data in data_sample:
                     # TODO: Used for HurricaneHarvey Dataset, Remove before implementing elsewhere, uncomment the if coding_subject, new_coding lines below.
                     # Currently doesn't work as query doesn't refresh ?

                    #Hardcoded shortcut to avoid coding spam tweets with specific URLs. Needs updating.
                    #if coding_subject == 'tweet':
                    #    spam_source_1 = 'Paper.li'
                    #    spam_source_2 = 'TweetMyJOBS'
                    #   ###if active_coding_dimension = VALUE_OF_MAIN_TWEET_DIMENSION #TODO: fix this so block only executes under main dimension.
                    #    if spam_source_1 in data.source or spam_source_2 in data.source:
                    #        print('Auto-coding Tweet as unrelated: {}'.format(data.text))
                    #        d_unrelated = DataCode.objects.get(data_code_id=7) #TODO: This ID will not work with new builds, must hard code the 'irrelevant' code here, add dimensionality
                    #        new_coding = Coding(tweet=data, data_code=d_unrelated) # Register sampled tweets as 'Unrelated'
                    #    else:
                    #        new_coding = Coding(tweet=data, data_code=d) # Register sampled tweets as 'To Be Coded'

                    if coding_subject=='tweet':                         # Remove these two lines if using the block above
                        new_coding = Coding(tweet=data, data_code=d)     ######
                    else:
                        new_coding = Coding(user=data, data_code=d)
                    try:
                        new_coding.save()
                    except IntegrityError as e:
                        pass
            data_query = data_to_be_coded
        else:
            data_query = data_coded_in_other_dimension

        #remaining = Tweet.objects.filter(data_source__gt=0).filter(~Q(datacode__data_code_id__gt=0)).count() #Too slow
        remaining = None
        count = data_query.count()
    else: # Secondary coders view only objects already coded by primary coder.
        # TODO: This is currently very slow, consider creating a 'to be coded' cache for secondary coder as done with primary above. Be careful that primary coder cache query above won't return these values.
        if coding_subject == 'tweet':
            data_query = Tweet.objects.filter(datacode__dimension_id=active_coding_dimension).filter(~Q(coding_for_tweet__in=Coding.objects.filter(coding_id=active_coder).filter(data_code__dimension__id=active_coding_dimension))) # Select coded Tweet which hasn't been coded by the current coder in the current dimension.
        else:
            data_query = User.objects.filter(datacode__dimension_id=active_coding_dimension).filter(~Q(coding_for_user__in=Coding.objects.filter(coding_id=active_coder).filter(data_code__dimension__id=active_coding_dimension))) # Select coded User which hasn't been coded by the current coder in the current dimension.
        count = data_query.count()
        remaining = count

    if count > 0:
        rand = random.randint(0, (count-1))
        data_object = data_query[rand]
    else:
        data_object = None

    if coding_subject == 'tweet':
        total_coded = Coding.objects.filter(coding_id=active_coder, tweet__isnull=False).filter(data_code__data_code_id__gt=0).filter(data_code__dimension_id=active_coding_dimension).count() #Total coded by current coder
    else:
        total_coded = Coding.objects.filter(coding_id=active_coder, user__isnull=False).filter(data_code__data_code_id__gt=0).filter(data_code__dimension_id=active_coding_dimension).count() #Total coded by current coder

    codes = DataCode.objects.filter(dimension__id=active_coding_dimension).order_by('data_code_id')

    return render(request, 'streamcollect/coding_interface.html', {'data_object': data_object, 'codes': codes, 'active_coder': active_coder, 'remaining': remaining, 'total_coded': total_coded, 'coding_subject': coding_subject})


# TODO: This function only functions for secondary_coder with coding_id=2, may need to adjust for more secondary coders when scaling. Template would also need adjusting.
def coding_results(request):

    active_coding_dimension = request.session.get('active_coding_dimension', None)
    is_tw_dimension = DataCodeDimension.objects.get(id=active_coding_dimension).coding_subject == 'tweet'

    total_main_coder = Coding.objects.filter(coding_id='1').filter(data_code__data_code_id__gt=0).filter(data_code__dimension_id=active_coding_dimension)
    total_secondary_coder = Coding.objects.filter(coding_id='2').filter(data_code__data_code_id__gt=0).filter(data_code__dimension_id=active_coding_dimension)

    if is_tw_dimension:
        double_coded_objs = Tweet.objects.filter(coding_for_tweet__coding_id = 2, coding_for_tweet__data_code__dimension = active_coding_dimension)
    else:
        double_coded_objs = User.objects.filter(coding_for_user__coding_id = 2, coding_for_user__data_code__dimension = active_coding_dimension)

    codes = DataCode.objects.filter(dimension=active_coding_dimension)

    total_table = [['', 'Primary', 'Percentage', 'Secondary']]
    disagree_table = []
    disagree_table.append([''] + list(codes.values_list('name', flat=True)) + ['Disagreement:', 'Of Total:'])
    index_dict = {}
    i = 1 # Start from 1 to skip headers
    for c in codes:
        total_table.append([c.name] + [0]*3)
        disagree_table.append([c.name] + [0]*codes.count())
        index_dict[c.name] = i
        i += 1

    # Populate summary table
    for c in total_main_coder:
        index = index_dict.get(c.data_code.name)
        total_table[index][1] += 1
        total_table[index][2] = '{:.1%}'.format(total_table[index][1] / total_main_coder.count())
    for c in total_secondary_coder:
        index = index_dict.get(c.data_code.name)
        total_table[index][3] += 1
    total_table.append(['', total_main_coder.count(), '', total_secondary_coder.count()])

    # Populate disagreement matrix
    for obj in double_coded_objs:
        if is_tw_dimension:
            coding1 = obj.coding_for_tweet.filter(coding_id=1)[0]
            coding2 = obj.coding_for_tweet.filter(coding_id=2)[0]
        else:
            coding1 = obj.coding_for_user.filter(coding_id=1)[0]
            coding2 = obj.coding_for_user.filter(coding_id=2)[0]
        disagree_table[index_dict.get(coding1.data_code.name)][index_dict.get(coding2.data_code.name)] += 1
    # Add proportion of disagreed codes by row
    i=1
    for row in disagree_table[1:]:
        if is_tw_dimension:
            total_double_coded = Tweet.objects.filter(coding_for_tweet__coding_id=2, coding_for_tweet__data_code__dimension_id=active_coding_dimension).filter(coding_for_tweet__coding_id=1, coding_for_tweet__data_code__name=row[0], coding_for_tweet__data_code__dimension_id=active_coding_dimension).count()
        else:
            total_double_coded = User.objects.filter(coding_for_user__coding_id=2, coding_for_user__data_code__dimension_id=active_coding_dimension).filter(coding_for_user__coding_id=1, coding_for_user__data_code__name=row[0], coding_for_user__data_code__dimension_id=active_coding_dimension).count()
        if total_double_coded > 0:
            prop = '{:.1%}'.format((sum(row[1:]) - row[i]) / total_double_coded)
        else:
            prop = '0%'
        row.append(prop)
        row.append(total_double_coded)
        i += 1
    # Add proportion of disagreed codes by col
    disagreement_cols = []
    total_cols = []
    i = 1
    while i < (len(disagree_table[0])-2):
        if is_tw_dimension:
            total_double_coded = Tweet.objects.filter(coding_for_tweet__coding_id=2, coding_for_tweet__data_code__dimension_id=active_coding_dimension, coding_for_tweet__data_code__name=disagree_table[0][i]).filter(coding_for_tweet__coding_id=1, coding_for_tweet__data_code__dimension_id=active_coding_dimension).count()
        else:
            total_double_coded = User.objects.filter(coding_for_user__coding_id=2, coding_for_user__data_code__dimension_id=active_coding_dimension, coding_for_user__data_code__name=disagree_table[0][i]).filter(coding_for_user__coding_id=1, coding_for_user__data_code__dimension_id=active_coding_dimension).count()
        total_disagreed = sum([x[i] for x in disagree_table[1:]]) - disagree_table[i][i]
        if total_double_coded > 0:
            prop = '{:.1%}'.format(total_disagreed / total_double_coded)
        else:
            prop = '0%'
        disagreement_cols.append(prop)
        total_cols.append(total_double_coded)
        i += 1
    disagree_table.append(['Disagreement:'] + disagreement_cols)
    disagree_table.append(['Of Total: '] + total_cols)

    #TODO: Check either Coding has no duplicate codes (this should now be handled in the models.py unique_together meta):
    #active_coding_dimension = request.session.get('active_coding_dimension', None)
    #for c in Coding.objects.filter(coding_id=1, data_code__id=active_coding_dimension):
    #  if c.tweet.coding.filter(coding_id=2, data_code__id=active_coding_dimension).count>1:
    #    c.delete()
    #

    #TODO: more practical to generate this matrix then format it rather than current other way around
    cont_mat = [ x[1:-2] for x in disagree_table[1:-2] ]
    agreement_coefs = calculate_agreement_coefs(cont_mat)

    return render(request, 'streamcollect/coding_results.html', {'total_table':total_table, 'disagree_table':disagree_table, 'agreement_coefs':agreement_coefs})


def coding_disagreement(request, coder1code, coder2code):

    active_coding_dimension = request.session.get('active_coding_dimension', None)
    is_tw_dimension = DataCodeDimension.objects.get(id=active_coding_dimension).coding_subject == 'tweet'
    print(is_tw_dimension)

    # Double lookup here to preserve the order of codes as originally passed to the html,
    # as it was not possible to pass the datacode back from the template due to the format
    # of the table loop. Therefore, have passed the forloop counter integers as indices.
    codes = DataCode.objects.filter(dimension=active_coding_dimension).values_list('name', flat=True)

    coder1code = DataCode.objects.get(name = codes[int(coder1code)])
    coder2code = DataCode.objects.get(name = codes[int(coder2code)])
    if is_tw_dimension:
        total_double_coded = Tweet.objects.filter(coding_for_tweet__coding_id=2, coding_for_tweet__data_code__dimension_id=active_coding_dimension, coding_for_tweet__data_code=coder2code).filter(coding_for_tweet__coding_id=1, coding_for_tweet__data_code__dimension_id=active_coding_dimension, coding_for_tweet__data_code=coder1code)
    else:
        total_double_coded = User.objects.filter(coding_for_user__coding_id=2, coding_for_user__data_code__dimension_id=active_coding_dimension, coding_for_user__data_code=coder2code).filter(coding_for_user__coding_id=1, coding_for_user__data_code__dimension_id=active_coding_dimension, coding_for_user__data_code=coder1code)

    objs = []
    for obj in total_double_coded:
        if is_tw_dimension:
            if obj.coding_for_tweet.filter(coding_id=1, data_code__dimension_id=active_coding_dimension)[0].data_code.data_code_id != obj.coding_for_tweet.filter(coding_id=2, data_code__dimension_id=active_coding_dimension)[0].data_code.data_code_id:
                objs.append(obj)
        else:
            if obj.coding_for_user.filter(coding_id=1, data_code__dimension_id=active_coding_dimension)[0].data_code.data_code_id != obj.coding_for_user.filter(coding_id=2, data_code__dimension_id=active_coding_dimension)[0].data_code.data_code_id:
                objs.append(obj)

    return render(request, 'streamcollect/coding_disagreement.html', {'objs': objs, 'is_tw_dimension': is_tw_dimension})


def view_entities(request):
    max_items = 50
    keywords = Keyword.objects.all().values_list('keyword', flat=True) #TODO: Keywords may have hashtags, whereas Hashtag objects don't.
    hashtags_with_counts = Hashtag.objects.exclude(hashtag__in=keywords).annotate(tweet_count=Count('tweets__id')).order_by('-tweet_count')[:max_items/2]
    urls_with_counts = Url.objects.all().annotate(tweet_count=Count('tweets__id')).order_by('-tweet_count')[:max_items]
    mentions_with_counts = Mention.objects.all().annotate(tweet_count=Count('tweets__id')).order_by('-tweet_count')[:max_items]

    return render(request, 'streamcollect/view_entities.html', {'hashtags': hashtags_with_counts, 'urls': urls_with_counts,  'mentions': mentions_with_counts})


def twitter_auth(request):
    tokens = AccessToken.objects.all()
    return render(request, 'streamcollect/twitter_auth.html', {'tokens': tokens})


def callback(request):
    try:
        ckey=ConsumerKey.objects.all()[:1].get()
    except ObjectDoesNotExist:
        print('Error! Failed to get Consumer Key from database.')
        return render(request, 'streamcollect/monitor_event.html')
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
        return redirect('monitor_event')

    elif "add_keyword_low" in request.POST:
        info = request.POST['info']
        redirect_to = request.POST['redirect_to']
        if len(info) > 0:
            k = Keyword()
            k.keyword = info.lower()
            k.created_at = timezone.now()
            k.priority = 1
            k.save()
        return redirect(redirect_to)

    elif "add_keyword_high" in request.POST: # TODO: fold into above method, add priority as hidden value
        info = request.POST['info']
        redirect_to = request.POST['redirect_to']
        if len(info) > 0:
            k = Keyword()
            k.keyword = info.lower()
            k.created_at = timezone.now()
            k.priority = 2
            k.save()
        return redirect(redirect_to)

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
        return redirect('stream_status')

    elif "start_gps_stream" in request.POST:
        try:
            event = Event.objects.all()[0]
        except:
            return redirect('view_event')
        if event.geopoint.all().count() == 2:
            lats = GeoPoint.objects.all().values_list('latitude', flat=True)
            lons = GeoPoint.objects.all().values_list('longitude', flat=True)
            gps = [min(lons), min(lats), max(lons), max(lats)]  # Ordering as SW, NE as per Twitter requirements
        elif event.geopoint.all().count() == 1:
            gps = [event.geopoint.all()[0].longitude, event.geopoint.all()[0].latitude]
        else: # No GPS coordinates
            return redirect('stream_status')
        if event.gps_stream_start is None or event.gps_stream_start > timezone.now():
            event.gps_stream_start = timezone.now()
            event.save()
        task = twitter_stream_task.delay(gps)
        return redirect('stream_status')

    elif "stop_kw_stream" in request.POST or "stop_gps_stream" in request.POST:
        ts = inspect(['celery@stream_worker']).active().get('celery@stream_worker')
        event = Event.objects.all()[0]
        for t in ts:
            task_id = t.get('id')
            if 'stop_kw_stream' in request.POST and 'priority' in t['kwargs']:
                revoke(task_id, terminate=True)
                if event.kw_stream_end is None or event.kw_stream_end < timezone.now():
                    event.kw_stream_end = timezone.now()
            elif 'stop_gps_stream' in request.POST and 'priority' not in t['kwargs']:
                revoke(task_id, terminate=True)
                if event.gps_stream_end is None or event.gps_stream_end < timezone.now():
                    event.gps_stream_end = timezone.now()
        event.save()
        return redirect('stream_status')

    elif "trim_spam_accounts" in request.POST:
        task = trim_spam_accounts.delay()
        return redirect('functions')

    elif "create_relos_from_list" in request.POST:
        task = update_user_relos_task.delay()
        return redirect('functions')

    elif "create_relos_from_list" in request.POST:
        task = create_relos_from_list_task.delay()
        return redirect('functions')

    elif "delete_keywords" in request.POST:
        Keyword.objects.all().delete()
        return redirect('functions')

    elif "terminate_tasks" in request.POST:
        ts = inspect(['celery@stream_worker']).active().get('celery@stream_worker') + inspect(['celery@object_worker']).active().get('celery@object_worker') + inspect(['celery@object_worker']).reserved().get('celery@object_worker') + inspect(['celery@media_worker']).active().get('celery@media_worker') + inspect(['celery@media_worker']).reserved().get('celery@media_worker')
        for t in ts:
            revoke(t.get('id'), terminate=True)
        return redirect('functions')

    elif "user_timeline" in request.POST:
        print("User Timeline Function...")
        save_user_timelines_task.delay()
        return redirect('functions')

    elif "update_data" in request.POST:
        update_tracked_tags()
        add_users_from_mentions()
        return redirect('functions')

    elif "update_screen_names" in request.POST:
        task = compare_live_data_task.delay()
        return redirect('functions')

    elif "twitter_auth" in request.POST: #TODO: No longer working?
        try:
            ckey=ConsumerKey.objects.all()[:1].get()
        except ObjectDoesNotExist:
            print('Error! Failed to get Consumer Key from database.')
            return render(request, 'streamcollect/monitor_event.html')
        auth = tweepy.OAuthHandler(ckey.consumer_key, ckey.consumer_secret, 'https://127.0.0.1:8000/callback')
        try:
            redirect_url = auth.get_authorization_url()
            request.session['request_token'] = auth.request_token
        except tweepy.TweepError:
            print('Error! Failed to get request token.')
            return render(request, 'streamcollect/monitor_event.html')
        return redirect(redirect_url)

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
            return render(request, 'streamcollect/monitor_event.html')
        tokens = AccessToken.objects.all()
        f = open('tokens_export.py', 'w')
        f.write('CONSUMER_KEY = \'' + ckey.consumer_key + '\'\n')
        f.write('CONSUMER_SECRET = \'' + ckey.consumer_secret + '\'\n')
        f.write('ACCESS_TOKENS = (\n')
        for t in tokens:
            f.write('\t' + t.__str__() + ',\n')
        f.write(')\n')
        f.write('MAPBOX_PK = \'' + MAPBOX_PK + '\'\n')
        f.close
        return redirect('twitter_auth')

    elif "add_data_code" in request.POST:
        code = request.POST['code']
        description = request.POST['description']
        if len(code) > 0:
            d = list(DataCode.objects.values_list('data_code_id', flat=True))
            data_code_id = min([i for i in list(range(1,100)) if i not in d]) # Smallest ID not already in use, will error if more than 100 codes created.
            active_coding_dimension = request.session.get('active_coding_dimension', None)
            try:
                dimension = DataCodeDimension.objects.get(id=active_coding_dimension)
                c = DataCode(name=code, description=description, data_code_id=data_code_id, dimension=dimension)
                c.save()
            except:
                pass
        return redirect('coding_dash')

    elif "delete_data_code" in request.POST:
        data_code_id = request.POST['data_code_id']
        data_code = DataCode.objects.filter(data_code_id=data_code_id)
        data_code.delete()
        return redirect('coding_dash')

    elif "assign_code" in request.POST:
        coding_subject = request.session.get('coding_subject', None)
        code_id = request.POST['assign_code']
        data_id = request.POST['data_id']
        coding_id = request.session.get('active_coder', 1)
        data_code = DataCode.objects.get(data_code_id=code_id)
        if coding_subject == 'tweet':
            tweet = Tweet.objects.get(tweet_id=data_id)
            coding = Coding(tweet=tweet, data_code=data_code, coding_id=coding_id) # Add new code classification
            Coding.objects.filter(tweet=tweet).filter(data_code__data_code_id=0).delete() # Delete 'To Be Coded' classification
        else:
            user = User.objects.get(user_id=data_id)
            coding = Coding(user=user, data_code=data_code, coding_id=coding_id) # Add new code classification
            Coding.objects.filter(user=user).filter(data_code__data_code_id=0).delete() # Delete 'To Be Coded' classification
        coding.save() #TODO: This may need Integrity error handling where it attempts to save the coding object twice (now prevented through the unique_together attribute)
        return redirect('coding_interface')

    elif "undo_code" in request.POST:
        coding_id = request.session.get('active_coder', 1)
        active_coding_dimension = int(request.session.get('active_coding_dimension'))
        last_coding = Coding.objects.filter(coding_id=coding_id, data_code__dimension__id=active_coding_dimension, data_code__data_code_id__gt=0).order_by('updated').last() # Get last coded object for active coder, in current dimension.
        if last_coding:
            if coding_id == 1:
                blank_data_code = DataCode.objects.get(data_code_id=0)
                last_coding.data_code = blank_data_code
                last_coding.save()
            else:
                last_coding.delete()
        return redirect('coding_interface')

    elif "set_code_dimension" in request.POST:
        dimension_id = request.POST['dimension_id']
        request.session['active_coding_dimension'] = int(dimension_id)
        return redirect('coding_dash')

    elif "add_dimension" in request.POST:
        name = request.POST['dimension_name']
        description = request.POST['description']
        coding_subject = request.session.get('coding_subject')
        if len(name) > 0:
            d = DataCodeDimension(name=name, description=description, coding_subject=coding_subject)
            d.save()
        return redirect('coding_dash')

    elif "delete_dimension" in request.POST:
        dimension_id = request.POST['dimension_id']
        DataCodeDimension.objects.filter(id=dimension_id).delete()
        if request.session.get('active_coding_dimension', None) == int(dimension_id):
            request.session['active_coding_dimension'] = None
        return redirect('coding_dash')

    elif "set_coding_subject" in request.POST:
        coding_subject = request.POST['coding_subject']
        request.session['coding_subject'] = coding_subject
        return redirect('coding_dash')

    elif "set_coder" in request.POST:
        coder_id = int(request.POST['coder_id'])
        request.session['active_coder'] = coder_id
        return redirect('coding_dash')

    elif "set_active_data_source" in request.POST:
        if 'data_source_to_activate' in request.POST:
            active_data_source = request.POST['data_source_to_activate']
            actives_list = request.session.get('active_data_sources', [])
            actives_list.append(int(active_data_source))
        elif 'data_source_to_deactivate' in request.POST: # TODO: on first load, this appears to deactivate all sources.
            deactive_data_source = request.POST['data_source_to_deactivate']
            actives_list = request.session.get('active_data_sources', [])
            try:
                actives_list.remove(int(deactive_data_source))
            except:
                pass
        request.session['active_data_sources'] = actives_list
        return redirect('monitor_event')

    elif "network_metrics" in request.POST:
        users = User.objects.filter(user_class=2)
        calculate_user_graph_metrics(users, Relo.objects.filter(source_user__user_class=2, target_user__user_class=2))
        calculate_user_stream_metrics(users)
        return redirect('functions')

    elif "save_coded_data_to_file" in request.POST:
        # Ouput all the data that has been coded by primary coder to file.
        coding_subject = request.session.get('coding_subject', None)
        if coding_subject == 'tweet':
            data = Tweet.objects.filter(coding_for_tweet__coding_id=1, coding_for_tweet__data_code__data_code_id__gt=0)
            with open('tweetData.csv', 'w') as csvFile:
                writer = csv.writer(csvFile)
                writer.writerow(data[0].as_row(header=True))
                for tweet in data:
                    writer.writerow(tweet.as_row())
            csvFile.close()
        elif coding_subject == 'user':
            data = User.objects.filter(coding_for_user__coding_id=1, coding_for_user__data_code__data_code_id__gt=0)
            with open('userData.csv', 'w') as csvFile:
                writer = csv.writer(csvFile)
                writer.writerow(data[0].as_row(header=True))
                for user in data:
                    writer.writerow(user.as_row())
            csvFile.close()
        return redirect('coding_dash')

    else:
        print("Unlabelled button pressed")
        return redirect('monitor_event')


#API returns users above a 'relevant in degree' threshold and the links between them
def network_data_API(request):
    print("Collecting network_data...")

    #All ego nodes, and alters with an in/out degree of X or greater.
    slice_size = 5000 #TODO: Change to a random sample
    #classed_users = User.objects.filter(user_class__gt=0).filter(Q(in_degree__gte=REQUIRED_IN_DEGREE) | Q(out_degree__gte=REQUIRED_OUT_DEGREE) | Q(user_class__gte=2))[:slice_size]
    # Ignore REQUIRED_IN/OUT_DEGREE
    #classed_users = User.objects.filter(user_class__gte=2)[:slice_size]
    #classed_users = User.objects.filter(user_class__gt=0).filter(Q(in_degree__gte=1) | Q(out_degree__gte=1) | Q(user_class__gte=2)) # Include alter nodes (requires running of trim_spam_accounts first)
    classed_users = User.objects.filter(user_class__gte=2) # Only ego nodes

    # Only show users which have had Tweets coded
    #coded_tweets = Tweet.objects.filter(coding_for_tweet__data_code__data_code_id__gt=0).filter(coding_for_tweet__coding_id=1)
    #coded_users = User.objects.filter(tweet__in=coded_tweets).filter(Q(in_degree__gte=REQUIRED_IN_DEGREE) | Q(out_degree__gte=REQUIRED_OUT_DEGREE))
    #coded_users = User.objects.filter(tweet__in=coded_tweets)

    # Users which are coded [ie. use this block to ensure all coded users are included in the output]
#     try:
#         dcd = DataCodeDimension.objects.filter(coding_subject='user')[0] # Default to first user dimension
#         #    coded_users = User.objects.filter(coding_for_user__in=Coding.objects.filter(coding_id='1').filter(data_code__data_code_id__gt=0).filter(data_code__dimension_id=dcd))
#         #TODO: This query can be made more efficient:
#         coded_users = User.objects.filter(coding_for_user__in=Coding.objects.filter(coding_id='1').filter(data_code__data_code_id__gt=0).filter(data_code__dimension_id=dcd))
#         coded_users_count = coded_users.count()
#     except:
#         coded_users_count = 0
# #    relevant_users = [x for x in classed_users] + [y for y in coded_users] # Creates list
#     #relevant_users = classed_users | coded_users
#     #relevant_users = [x for x in classed_users]

    #print("Coded Users (by tweet): {}, Classed Users: {}, Relevant Users: {}".format(coded_users_count, classed_users.count(), len(relevant_users)))

    # Get relationships which connect two 'relevant users'. This is slow. Could pre-generate?
    print("Creating Relo JSON..")
    relevant_relos = Relo.objects.filter(target_user__in=classed_users, source_user__in=classed_users, end_observed_at=None)

    print("Writing GEXF file..")
    create_gephi_file(classed_users, relevant_relos)

    # resultsrelo = [ob.as_json() for ob in relevant_relos]
    # print("Total Relos: {}".format(len(resultsrelo)))
    #
    # #Remove isolated nodes: TODO: May be too slow
    # if EXCLUDE_ISOLATED_NODES:
    #     print("Excluding Isolated Nodes..")
    #     targets = list(relevant_relos.values_list('target_user', flat=True))
    #     sources = list(relevant_relos.values_list('source_user', flat=True))
    #
    #     relo_node_list = targets + list(set(sources) - set(targets))
    #     print("Creating User JSON..")
    #     resultsuser = [ob.as_json() for ob in relevant_users if ob.id in relo_node_list]
    # else:
    #     print("Creating User JSON..")
    #     resultsuser = [ob.as_json() for ob in relevant_users]
    #
    # data = {"nodes" : resultsuser, "links" : resultsrelo}
    # jsondata = json.dumps(data)

    #TODO: HttpReponse vs Jsonresponse? Latter doesn't work with current d3
    # return HttpResponse(jsondata)

    # TEMP return while HttpResponse above is commented out
    return redirect('monitor_event')
