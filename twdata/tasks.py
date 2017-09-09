from celery import shared_task

from .twitter_data import twitter_stream

@shared_task
def twitter_stream_task(gps=False, priority=0):
    twitter_stream(gps, priority)
    return
