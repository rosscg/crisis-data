Twitter social network data collection
==================================

App currently either takes screen name as input and saves data to DB, or takes
keywords to monitor for in stream. Streamed tweets are saved and their author's
data saved to the DB.

The build uses a fork of Tweepy which allows multiple tokens to be used.



Local installation:
------------
Install Redis from https://redis.io/ or brew, and follow instructions.
This build uses Postgres (over sqlite) as a database due to high write demands.
https://djangogirls.gitbooks.io/django-girls-tutorial-extensions/optional_postgresql_installation/
Build project, create virtual environment, and install dependencies.

Run Server: $ python manage.py runserver
  Log in to the admin interface and add a period task to 'update_user_relos_task' daily (alternatively, remove comment from update_user_relos_periodic in tasks.py)
Run Redis (from Redis directory): $ /redis-3.2.9/src/redis-server
Run Celery worker: $ celery -A homesite worker -l info
Run Celery beat: $ celery -A homesite beat -l info -S django

Fill out tokensSKELETON.py with Twitter credentials and rename tokens.py (tokens
must then be loaded to database via web interface). At the very least, the
consumer key and secret must be added to the file and loaded. Additional access
tokens can be added via the web interface, requiring a user to log in to Twitter
and authorise. 'Export Tokens' can save these tokens to a file for future use.



Note:
If Redis is running from previous launch (i.e. returns 'bind: Address already in use'):
$ ps aux | grep redis
$ kill -9 [PORT NUMBER]
