App currently takes screen name as input and saves data to DB.

Streaming functionality tracks keywords and adds associated users to DB (does not save tweet)

If multiple Twitter tokens are intended to be used, the fork of Tweepy must be installed instead.

Local installation:
Install Redis from https://redis.io/ or brew, and follow instructions.
Build project, create virtual environment, and install dependencies.

Run Server: $ python manage.py runserver
  Log in to the admin interface and add a period task to 'update_user_relos_task' daily (alternatively, remove comment from update_user_relos_periodic in tasks.py)
Run Redis (from Redis directory): $ /redis-3.2.9/src/redis-server
Run Celery worker: $ celery -A homesite worker -l info
Run Celery beat: $ celery -A homesite beat -l info -S django
