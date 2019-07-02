Twitter social network data collection
==================================

This application is designed to collect user network data from Twitter using keyword and GPS streams. Rich user data is recorded, including their follower/following network. This network data can then be monitored for changes over time.

The build uses a fork of Tweepy which allows multiple tokens to be used.

Note: Excluding Tweets containing the term 'pray' is hard-coded to reduce unnecessary content (as the original application involved disaster events).

==================================

Local installation (Mac):
------------
* Install python3.
* Install Postgres.app, configure `$PATH` as detailed in step 3 [here](http://postgresapp.com/) (tested with v9.6).
* This build uses Postgres (over sqlite) as a database due to high write demands
* Create database from Postgres command line:

        > ```
        > $ psql
        > $ CREATE DATABASE [dbname];
        > ```

* Turn off auto-sleep / install Caffeine (Mac) (only necessary during data collection).
* Install Redis from https://redis.io/ or brew, and build:

        > ```
        > $ cd redis-4.0.1
        > $ make
        > $ make test
        > $ src/redis-server
        > ```

* You may need to install SSL certificates if using python 3.6, simply run `/Applications/Python 3.6/Install Certificates.command` as explained [here](https://bugs.python.org/issue28150).
* Clone this project and open its directory. Create virtual environment and install dependencies. Pip should be included in the venv, otherwise may need to install manually. The pip command below avoids using cache due to pip bug:

        > ```
        > $ git clone https://github.com/rosscg/crisis-data.git
        > $ cd crisis-data
        > $ python3 -m venv venv
        > $ source venv/bin/activate
        > $ pip install -r requirements.txt --no-cache-dir
        > ```

* Check if Hardcoded auto-coding line is still in `views.py` - from approx line 150 and remove (uncomment appropriate line beneath block).

* Set database name, username and password in `homesite/settings.py`, line ~84.
Default username is the system user name, default password is none.

* Re-name `streamcollect/tokensSKELETON.py` to `tokens.py` and add (at least) `CONSUMER_KEY` and `CONSUMER_SECRET` (generated from https://apps.twitter.com/).

* Run Redis (from Redis Directory), Celery Worker and Celery Beat in separate terminal windows:

        > ```
        > $ redis-4.0.1/src/redis-server
        > $ celery -A homesite worker --concurrency=4 -l info -n object_worker -Q save_object_q
        > $ celery -A homesite worker --concurrency=4 -l info -n stream_worker -Q stream_q
        > $ celery -A homesite worker --concurrency=4 -l info -n media_worker -Q save_media_q
        > $ celery -A homesite beat -l info -S django
        > ```
  * Note: `--concurrency=4` should be the number of cores in the system, can remove to default to this value, but need to update `CONCURRENT_TASKS` to the same value.

* Migrate database and run server:

        > ```
        > $ python manage.py migrate
        > $ python manage.py runserver
        > ```

 * Optional: Log in to the admin interface and add a period task to `update_user_relos_task` daily (alternatively, remove comment from `update_user_relos_periodic` in `tasks.py`)

* Load Twitter authentication details with the 'Load From Config' button on the Twitter Authentication page.
  * Additional access tokens can be added via the web interface, requiring a user to log in to Twitter and authorise. 'Export Tokens' can save these tokens to a file for future use.
  * Streams currently need at least 3 tokens added (one for each stream).

Notes:
* If Redis is running from previous launch (i.e. returns `bind: Address already in use`) find the port number (second column) and kill:

        > ```
        > $ ps aux | grep redis
        > $ kill -9 [PORT NUMBER]
        > ```

* Any change to the code requires Celery terminal commands to be relaunched.


Usage - Data Collection:
------------
The key functionality of the software is tracking keywords and GPS coordinates.

* If necessary, create new database in Postgres and adjust in `settings.py`.
* Edit `config.py` details as needed.
    * The exclusions aim to reduce the amount of processing and noise but affect the sample and therefore need to be considered with respect to the proposed analysis.
* Decide on periodic tasks in `tasks.py` (uncomment the decorators to run, requires the celery beat running).
    * `update_user_relos_periodic` is very intensive and will exhaust the API limits quickly, so is generally best left until after the stream collection.
    * `update_data_periodic allows` new hashtags to be added to the tracked tags depending on their prevalence in the detected Tweets. `REFRESH_STREAM` should be set to true, to add the new tags periodically.
* Create the event object - at the least it needs a name. Optionally add coordinates for the geo stream.
* Add keywords. Keywords cannot include spaces.
* High-priority keywords run as normal, low-priority keywords are saved when the queue is not full. Use this to reduce load.
* Run streams, disable OS auto-sleep.

After collection:

* Stop streams, wait for remaining tasks to resolve (could take some time). If there is a queue of tasks, the stream may continue to run until its termination is processed.
* Create a dump of the database (see below). Do this at other relevant milestones.
* Run trim_spam_accounts.
* Run save_user_timelines.
* Run update_relationship_data after a suitable time period (slow process due to rate limits). This currently only supports running once. Running again will damage the data by overwriting the `user_network_update_observed_at` value.
* Run `create_relos_from_list`.
* Optional: Add codes and code Tweets. Database supports up to 9 coders (though UI only supports 2). See section below.
* Export to suitable format for analysis (to be implemented) or access via notebooks.

Information on dumping the database to a file (for backup) can be found [here](https://www.postgresql.org/docs/9.1/static/backup-dump.html).

> ```
> $ pg_dump dbname > outfile
> $ createdb dbname2
> $ psql dbname2 < infile
> ```

To flush Redis DB (to clear queue of tasks):
> ```
> $ redis-4.0.1/src/redis-cli flushdb
> $ celery purge
> ```


Usage - Data Coding:
------------
Once the collection is complete, use the 'Data Coding' interface to code the Tweets. If it has been some time since data collection and you plan to code user objects, it is recommended to run the 'update_screen_names' function, as the source window will not work if the user has changed their screen name since collection.

From the 'Coding Dashboard', add the code dimension (or add a generic name if multiple dimensions are unneeded) then add the codes. From this page, the current code dimension and coder id can be selected before launching the coding interface.

The coding interface link will open three new windows - the top is the main interface. The other two larger windows show the source and either the Tweet feed that occurred during the event (in the case of user coding), or the target of the first URL included in the message (when coding Tweets).
Objects are randomly displayed from a pool of 10 and can be coded either by using the buttons or keyboard.

If selected from the coding dashboard, the secondary coder will be presented with any objects that have been coded by the primary coder. This is intended for coding schema validation purposes. The database supports more than two coders, but require relevant buttons to be implemented on the dash.

The results link will show the proportions distributed to each code, and the disagreement matrix for the two coders.

Note:
* Currently only one url from a Tweet is shown in the lower-right window, but in rare cases a Tweet may contain multiple urls.
* If the Tweet (or user) has been deleted and therefore is not displayed in the bottom-left window, the original text content can still be seen by scrolling down in the top interface window.


Usage - Data Analysis:
------------
The build can host python notebooks which use Django to access models. Run the notebook server with:

> ```
>$ cd notebooks
>$ ../manage.py shell_plus --notebook
> ```

Note: To run the notebook from outside of the Django directory, see the answer [here](https://stackoverflow.com/questions/35483328/how-to-setup-jupyter-ipython-notebook-for-django).


Remote Access:
------------
Use [ngrok](https://ngrok.com/) to serve the site remotely: `./ngrok http 8000`. Create an account and add your authtoken to avoid 8-hour timeout.

To enable notebooks via ngrok, remote access needs to be enabled:
* Create a config file: `$ jupyter notebook --generate-config`
* Edit the config file by uncommenting the line containing `c.NotebookApp.allow_remote_access` and set to `True`.
* Set a password for the notebook server: `$ jupyter notebook password`
* Run ngrok `./ngrok http 8888`
