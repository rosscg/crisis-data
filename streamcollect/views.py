from django.shortcuts import render, get_object_or_404, redirect
from .models import User, Relo
from .forms import AddUserForm
from twdata import userdata
from twdata.tasks import twitter_stream_task
from dateutil.parser import *
import json
from django.http import HttpResponse
#from django.db.models import Count
from django.utils import timezone
import datetime
from django.db.models import Q

import time

from streamcollect.tasks import add_user_task, update_user_relos_task

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
    add_user_task.delay(screen_name = info)
    return redirect('list_users')

#TODO: Remove this, and the import datetime line, and link from base template
def delete_today(request):
    yes = datetime.date.today() - datetime.timedelta(days=1)
    #yes = timezone.date.today() - timezone.timedelta(days=1)
    User.objects.filter(added_at__gt=yes).delete()
    Relo.objects.filter(observed_at__gt=yes).delete()
    return redirect('list_users')

def update_relos(request):
    #update_user_relos_task.delay()
    print("running task")
    task = twitter_stream_task.delay()
    print(len(task))
    print(type(task))
    time.sleep(20)
    print("killing task: {}".format(task))
    task.revoke(terminate=True)
    return redirect('list_users')


#API returns users above a 'relevant in degree' threshold and the links between them
def network_data_API(request):
    print("Collecting network_data...")

    required_in_degree = 3
    required_out_degree = 3

    #Include users with an in or out degree of X or greater
    relevant_users = User.objects.filter(Q(in_degree__gte=required_in_degree) | Q(out_degree__gte=required_out_degree))
    resultsuser = [ob.as_json() for ob in relevant_users]
    #Get relationships which connect two 'relevant users'
    resultsrelo = [ob.as_json() for ob in Relo.objects.filter(targetuser__in=relevant_users, sourceuser__in=relevant_users).filter(end_observed_at=None)]

    data = {"nodes" : resultsuser, "links" : resultsrelo}
    jsondata = json.dumps(data)

    return HttpResponse(jsondata)
