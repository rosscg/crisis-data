from celery import shared_task

from .twitter_data import twitter_stream
#from streamcollect.models import CeleryTask
from streamcollect.config import STREAM_REFRESH_RATE


@shared_task(bind=True, soft_time_limit=STREAM_REFRESH_RATE, max_retries=None, name='tasks.stream', queue='stream_q')
def twitter_stream_task(self, gps=False, priority=1):
    try:
        twitter_stream(gps, priority)
    except Exception as e:
        print('Error with stream: {}, retrying'.format(e))
        self.retry(countdown=5) # This is the easier way to restart the stream with new KWs.
        pass
    return
