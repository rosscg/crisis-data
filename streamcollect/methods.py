from .models import CeleryTask
from celery.task.control import revoke
from .config import FRIENDS_THRESHOLD, FOLLOWERS_THRESHOLD, STATUSES_THRESHOLD


def kill_celery_task(task_name):
    for t in CeleryTask.objects.filter(task_name=task_name):
        print("Killing task {}: {}".format(task_name, t.celery_task_id))
        revoke(t.celery_task_id, terminate=True)
        t.delete()

def check_spam_account(userdict):
    # Reject users with high metrics - spam/celebrity/news accounts
    print("Checking user as spam: {}".format(userdict.get('screen_name')))
    if userdict.get('followers_count') > FOLLOWERS_THRESHOLD:
        print('Rejecting user with high follower count: {}'.format(userdict.get('followers_count')))
        return True
    if userdict.get('friends_count') > FRIENDS_THRESHOLD:
        print('Rejecting user with high friends count: {}'.format(userdict.get('friends_count')))
        return True
    if userdict.get('statuses_count') > STATUSES_THRESHOLD:
        print('Rejecting user with high status count: {}'.format(userdict.get('statuses_count')))
        return True
    else:
        print("User {} passed test.".format(userdict.get('screen_name')))
        return False
