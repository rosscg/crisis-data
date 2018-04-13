Twitter social network data collection
==================================

This application is designed to collect user network data from Twitter using keyword and GPS streams. Rich user data is recorded, including their follower/following network. This network data can then be monitored for changes over time.

The build uses a fork of Tweepy which allows multiple tokens to be used.

Note: Excluding Tweets containing the term 'pray' is hard-coded to reduce unnecessary content (as the original application involved disaster events).

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


Usage - Data Collection:
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


Usage - Data Coding:
------------
Once the collection is complete, use the 'Data Coding' interface to code the Tweets.

From the 'Coding Dashboard', add the code dimension (or add a generic name if multiple dimensions are unneeded) then add the codes. From this page, the current code dimension and coder id can be selected before launching the coding interface.

The coding interface link will open three new windows - the top is the main interface. The other two larger windows show the original Tweet and linked content if included in the Tweet.
Tweets are randomly displayed from a pool of 100 and can be coded either by using the buttons or keyboard.

If selected from the coding dashboard, the secondary coder will be presented with any Tweets that have been coded by the primary coder. This is intended for coding schema validation purposes. The database supports more than two coders, but require relevant buttons to be implemented on the dash.

Note:
  Currently only one url from a Tweet is shown in the lower-right window, but in rare cases a Tweet may contain multiple urls.
  If the Tweet (or user) has been deleted and therefore is not displayed in the bottom-left window, the original text content can still be seen by scrolling down in the top interface window.
