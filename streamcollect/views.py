from django.shortcuts import render, get_object_or_404
from .models import User, Relo
from .forms import AddUserForm
from twdata import userdata
from dateutil.parser import *
from django.shortcuts import redirect
import json
from django.http import HttpResponse
#from django.db.models import Count
from django.utils import timezone
import datetime

from streamcollect.tasks import add_user_task

def monitor_user(request):
    return render(request, 'streamcollect/monitor_user.html', {})

def list_users(request):
    users = User.objects.filter(screen_name__isnull=False)
    return render(request, 'streamcollect/list_users.html', {'users': users})

def view_network(request):
    return render(request, 'streamcollect/view_network.html')

def user_details(request, user_id):
    user = get_object_or_404(User, user_id=user_id)
    return render(request, 'streamcollect/user_details.html', {'user': user})

def submit(request):
    info = request.POST['info']
    #add_user(info)
    add_user_task.delay(info)
    return redirect('list_users')

def delete_today(request):
    yes = datetime.date.today() - datetime.timedelta(days=1)
    User.objects.filter(added_at__gt=yes).delete()
    Relo.objects.filter(observed_at__gt=yes).delete()
    return redirect('list_users')


def add_user(info):
    #Get user information
    userdict = userdata.usernamedata(info)

    #See if user exists as a full user, or an existing target node.
    if User.objects.filter(screen_name=userdict.get('screen_name')).exists():
        print("User {} already exists.".format(info))

    else:
        if User.objects.filter(user_id=int(userdict.get('id_str'))).exists():

            #Updating user object
            print("Updating record...")
            #u = User.objects.filter(user_id=int(userdict.get('id_str')))
            u = get_object_or_404(User, user_id=int(userdict.get('id_str')))

            #TODO REMOVE THIS
            u.relevant_in_degree = u.relevant_in_degree + 5

        else:
            #Creating user object
            print("Creating record...")
            u = User()

            #TODO REMOVE THIS
            u.relevant_in_degree = 5

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
        u.user_id = int(userdict.get('id_str'))
        u.utc_offset = userdict.get('utc_offset')
        u.verified = userdict.get('verified')

        u.save()

        #Get users followed by account
        userfollowing = userdata.userfollowing(userdict.get('screen_name'))

        #Create relationship objects
        for targetuser in userfollowing:
            r = Relo()

            r.sourceuser = u

            #Create new users for targets if not already in DB
            if User.objects.filter(user_id=targetuser).exists():
                tuser = User.objects.get(user_id=targetuser)
                tuser.relevant_in_degree = tuser.relevant_in_degree + 1
                tuser.save()

                r.targetuser = tuser

            else:
                u2 = User()
                u2.user_id = targetuser
                u2.relevant_in_degree = 1
                u2.save()

                r.targetuser = u2
            r.save()

        #Get followers
        userfollowers = userdata.userfollowers(userdict.get('screen_name'))

        #Create relationship objects
        for sourceuser in userfollowers:
            r = Relo()

            r.targetuser = u

            #Create new users for targets if not already in DB
            if User.objects.filter(user_id=sourceuser).exists():
                r.sourceuser = User.objects.get(user_id=sourceuser)
            else:
                u2 = User()
                u2.user_id = sourceuser
                u2.save()
                r.sourceuser = u2
            r.save()
    return

#API returns users above a 'relevant in degree' threshold and the links between them
def network_data_API(request):
    print("Pulling network_data...")

    #Include users with an in degree of X or greater
    relevant_users = User.objects.filter(relevant_in_degree__gte=2)
    resultsuser = [ob.as_json() for ob in relevant_users]
    #Get relationships which connect two 'relevant users'
    resultsrelo = [ob.as_json() for ob in Relo.objects.filter(targetuser__in=relevant_users, sourceuser__in=relevant_users)]

    data = {"nodes" : resultsuser, "links" : resultsrelo}
    jsondata = json.dumps(data)

    return HttpResponse(jsondata)
