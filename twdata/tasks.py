from celery import shared_task

from .twitter_data import twitter_stream
#from streamcollect.models import CeleryTask
from streamcollect.config import STREAM_REFRESH_RATE


@shared_task(bind=True, soft_time_limit=STREAM_REFRESH_RATE, max_retries=None, name='tasks.stream', queue='stream_q')
def twitter_stream_task(self, gps=False, priority=1):
    try:
        twitter_stream(gps, priority)
    except:
        self.retry(countdown=1) # This is the easier way to restart the stream with new KWs.
        pass
    #CeleryTask.objects.get(celery_task_id=self.request.id).delete()
    return
