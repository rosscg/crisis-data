from django.shortcuts import render, get_object_or_404, redirect
from .models import User, Relo, CeleryTask
from .forms import AddUserForm
from twdata import userdata
from twdata.tasks import twitter_stream_task
from dateutil.parser import *
import json
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Q

from celery.task.control import revoke

from streamcollect.tasks import add_user_task, update_user_relos_task
from .config import REQUIRED_IN_DEGREE, REQUIRED_OUT_DEGREE

#TODO: Move to above line after testing
from .tasks import trim_spam_accounts

def test(request):
    task = trim_spam_accounts.delay()
    #task = update_user_relos_task.delay()
    print("running task: {}".format(task.task_id))
    task_object = CeleryTask(celery_task_id = task.task_id, task_name='trim_spam_accounts')
    task_object.save()
    return redirect('list_users')

def monitor_user(request):
    return render(request, 'streamcollect/monitor_user.html', {})

def list_users(request):
    users = User.objects.filter(user_class__gte=2)
    return render(request, 'streamcollect/list_users.html', {'users': users})

def view_network(request):
    return render(request, 'streamcollect/view_network.html')

def user_details(request, user_id):
    user = get_object_or_404(User, user_id=user_id)
    return render(request, 'streamcollect/user_details.html', {'user': user})

def submit(request):
    info = request.POST['info']
    add_user_task.delay(screen_name = info)
    return redirect('monitor_user')

def start_stream(request):
    task = twitter_stream_task.delay()
    print("running task: {}".format(task.task_id))
    task_object = CeleryTask(celery_task_id = task.task_id, task_name='stream_kw')
    task_object.save()
    return redirect('list_users')

def stop_stream(request):
    for t in CeleryTask.objects.filter(task_name='stream_kw'):
        print("killing task: {}".format(t.celery_task_id))
        revoke(t.celery_task_id, terminate=True)
        t.delete()
    return redirect('view_network')


#API returns users above a 'relevant in degree' threshold and the links between them
def network_data_API(request):
    print("Collecting network_data...")

    #Users with an in/out degree of X or greater, exclude designated spam.
    #TODO: Add ego users with smaller degrees?
    relevant_users = User.objects.filter(user_class__gte=0).filter(Q(in_degree__gte=REQUIRED_IN_DEGREE) | Q(out_degree__gte=REQUIRED_OUT_DEGREE))

    resultsuser = [ob.as_json() for ob in relevant_users]

    #Get relationships which connect two 'relevant users'. This is slow. Could pre-generate?
    relevant_relos = Relo.objects.filter(targetuser__in=relevant_users, sourceuser__in=relevant_users, end_observed_at=None)
    resultsrelo = [ob.as_json() for ob in relevant_relos]

    data = {"nodes" : resultsuser, "links" : resultsrelo}
    jsondata = json.dumps(data)

    #TODO: HttpReponse vs Jsonresponse? Latter doesn't work with current d3
    return HttpResponse(jsondata)
