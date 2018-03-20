Twitter social network data collection
==================================

App currently either takes screen name as input and saves data to DB, or takes
keywords to monitor for in stream. Streamed tweets are saved and their author's
data saved to the DB.

The build uses a fork of Tweepy which allows multiple tokens to be used.

Note: Excluding Tweets containing the term 'pray' is hard-coded to reduce unnecessary content.

==================================

Local installation (Mac):
------------
Install python3.
Install Postgres.app, configure $PATH as detailed in step 3 (tested with v9.6): http://postgresapp.com/
This build uses Postgres (over sqlite) as a database due to high write demands
Create database from Postgres command line:

> ```
> $ psql
> $ CREATE DATABASE [dbname];
> ```

Turn off auto-sleep / install Caffeine (Mac) (only necessary during data collection).

Install Redis from https://redis.io/ or brew, and build:

> ```
> $ cd redis-4.0.1
> $ make
> $ make test
> $ src/redis-server
> ```

Clone this project and open directory. Create virtual environment and install dependencies. Pip should be included in the venv, otherwise may need to install manually:

> ```
> $ git clone https://github.com/rosscg/crisis-data.git
> $ cd crisis-data
> $ python3 -m venv venv
> $ source venv/bin/activate
> $ pip install -r requirements.txt
> ```

Set database name [dbname], username and password in homesite/settings.py, line ~91.
Default username is the system user name, default password is none.

Re-name streamcollect/tokensSKELETON.py to tokens.py and add (at least) CONSUMER_KEY and CONSUMER_SECRET (generated from https://apps.twitter.com/).

Run Redis (from Redis Directory), Celery Worker and Celery Beat in separate terminal windows:

> ```
> $ redis-4.0.1/src/redis-server
> $ celery -A homesite worker  --concurrency=10 -l info
> $ celery -A homesite beat -l info -S django
> ```

Migrate database and run server:
> ```
> $ python manage.py migrate
> $ python manage.py runserver
> ```

  OPTIONAL: Log in to the admin interface and add a period task to 'update_user_relos_task' daily (alternatively, remove comment from update_user_relos_periodic in tasks.py)

Load Twitter authentication details with the 'Load From Config' button on the Twitter Authentication page.
Additional access tokens can be added via the web interface, requiring a user to log in to Twitter and authorise. 'Export Tokens' can save these tokens to a file for future use.
Streams currently need at least 3 tokens added (one for each stream).

Notes:
If Redis is running from previous launch (i.e. returns 'bind: Address already in use'):
> ```
> $ ps aux | grep redis
> $ kill -9 [PORT NUMBER]
> ```

Any change to the code requires Celery terminal commands to be relaunched.


Usage:
------------
The key functionality of the software is tracking keywords and GPS coordinates.

If necessary, create new database in Postgres and adjust in settings.py.
Edit config.py details as needed.
Decide on periodic tasks in tasks.py (uncomment the decorators to run, requires the celery beat running).
  update_user_relos_periodic is very intensive and will exhaust the API limits quickly, so is generally best left until after the stream collection.
  update_data_periodic allows new hashtags to be added to the tracked tags depending on their prevalence in the detected Tweets. REFRESH_STREAM should be set to true, to add the new tags periodically.
Add keywords and/or coordinates. Coordinates currently must be hard-coded into views.py
High-priority keywords run as normal, low-priority return a proportion of the tweets as set in config.py. Use this to reduce load.
Run streams, disable OS auto-sleep.

After collection:
  Stop streams, wait for remaining tasks to resolve (could take some time). If there is a queue of tasks, the stream may continue to run until it's termination is processed.
  Run trim_spam_accounts.
  Run save_user_timelines.
  Run update_relationship_data after a suitable time period (slow process due to rate limits).
  Optional: Add codes and code Tweets. System supports up to 9 coders (though 3-9 need to use direct URL as no buttons in place).
  Export to suitable format for analysis (to be implemented).

Information on dumping the database to a file (for backup) can be found here:
https://www.postgresql.org/docs/9.1/static/backup-dump.html

> ```
> $ pg_dump dbname > outfile
> $ createdb dbname2
> $ psql dbname2 < infile
> ```

To flush Redis DB:
> ```
> $ redis-4.0.1/src/redis-cli flushdb
> $ celery purge
> ```
