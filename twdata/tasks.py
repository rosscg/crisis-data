from celery import shared_task

from .twitter_data import twitter_stream

@shared_task
def twitter_stream_task(data=False):
    twitter_stream(data)
    return
