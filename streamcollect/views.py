from django.shortcuts import render
from .models import User, Relo
from .forms import AddUserForm
from twdata import userdata
from dateutil.parser import *

#imported for testing:
import json
from django.http import HttpResponse

from django.db.models import Count


def monitor_user(request):
    return render(request, 'streamcollect/monitor_user.html', {})

def show_user(request):
    users = User.objects.all()
    return render(request, 'streamcollect/show_user.html', {'users': users})

def view_network(request):
    return render(request, 'streamcollect/view_network.html')

def network_data_API(request):
    print("Pulling network_data...")
    resultsuser = [ob.as_json() for ob in User.objects.all()]
    #TODO This line takes too long:
    resultsrelo = [ob.as_json() for ob in Relo.objects.all()]
    data = {"nodes" : resultsuser, "links" : resultsrelo}
    jsondata = json.dumps(data)

    return HttpResponse(jsondata)

def submit(request):
    info = request.POST['info']

    #Get user information
    userdict = userdata.usernamedata(info)

    #Create user object
    u = User()

    u.contributors_enabled = userdict.get('contributors_enabled')
    u.created_at = parse(userdict.get('created_at'))
    u.default_profile = userdict.get('default_profile')
    u.default_profile_image = userdict.get('default_profile_image')
    u.description = userdict.get('description')
    #TODO entities = NOT YET IMPLEMENTED
    u.favourites_count = userdict.get('favourites_count')
    u.followers_count = userdict.get('followers_count')
    u.friends_count = userdict.get('friends_count')
    u.geo_enabled = userdict.get('geo_enabled')
    u.has_extended_profile = userdict.get('has_extended_profile')
    u.id = int(userdict.get('id_str'))
    u.is_translation_enabled = userdict.get('is_translation_enabled')
    u.is_translator = userdict.get('is_translator')
    u.lang = userdict.get('lang')
    u.listed_count = userdict.get('listed_count')
    u.location = userdict.get('location')
    u.name = userdict.get('name')
    u.needs_phone_verification = userdict.get('needs_phone_verification')
    u.notifications = userdict.get('notifications')
    u.profile_background_color = userdict.get('profile_background_color')
    u.profile_background_image_url = userdict.get('profile_background_image_url')
    u.profile_background_image_url_https = userdict.get('profile_background_image_url_https')
    u.profile_background_tile = userdict.get('profile_background_tile')
    u.profile_image_url = userdict.get('profile_image_url')
    u.profile_image_url_https = userdict.get('profile_image_url_https')
    u.profile_link_color = userdict.get('profile_link_color')
    u.profile_location = userdict.get('profile_location')
    u.profile_sidebar_border_color = userdict.get('profile_sidebar_border_color')
    u.profile_sidebar_fill_color = userdict.get('profile_sidebar_fill_color')
    u.profile_text_color = userdict.get('profile_text_color')
    u.profile_use_background_image = userdict.get('profile_use_background_image')
    u.protected = userdict.get('protected')
    u.screen_name = userdict.get('screen_name')
    u.statuses_count = userdict.get('statuses_count')
    u.suspended = userdict.get('suspended')
    u.time_zone = userdict.get('time_zone')
    u.translator_type = userdict.get('translator_type')
    u.url = userdict.get('url')
    u.utc_offset = userdict.get('utc_offset')
    u.verified = userdict.get('verified')

    u.save()

    #Get users followed by account
    userfollowing = userdata.userfollowing(info)

    #Create relationship objects
    for targetuser in userfollowing:
        r = Relo()

        r.sourceuser = u

        #Create new users for targets if not already in DB
        if User.objects.filter(id=targetuser).exists():
            r.targetuser = User.objects.get(id=targetuser)
        else:
            u2 = User()
            u2.id = targetuser
            u2.save()
            r.targetuser = u2
        r.save()

    #Get followers
    userfollowers = userdata.userfollowers(info)

    #Create relationship objects
    for sourceuser in userfollowers:
        r = Relo()

        r.targetuser = u

        #Create new users for targets if not already in DB
        if User.objects.filter(id=sourceuser).exists():
            r.sourceuser = User.objects.get(id=sourceuser)
        else:
            u2 = User()
            u2.id = sourceuser
            u2.save()
            r.sourceuser = u2
        r.save()


    users = User.objects.all()
    return render(request, 'streamcollect/show_user.html', {'users': users})
