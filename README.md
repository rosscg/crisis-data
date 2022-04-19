# Twitter social network data collection
==================================

This application is designed to collect user network data from Twitter using keyword and GPS streams. Rich user data is recorded, including their follower/following network. This network data can then be monitored for changes over time.

Manual coding is supported for both user accounts and individual Tweets.

Data is stored in a local database and support is included to access the data from within Jupyter notebooks.

The build uses a fork of Tweepy which allows multiple Twitter API tokens to be used.

------------
### Installation with Docker:

* Clone repository
* Re-name `streamcollect/tokensSKELETON.py` to `tokens.py` and add (at least) `CONSUMER_KEY` and `CONSUMER_SECRET` (from the [Twitter Dev Portal](https://developer.twitter.com/apps)).

* Install [Docker](https://www.docker.com/products/docker-desktop)
* Increase memory in Docker to ~4gb (exit code 137 denotes out of memory error)
* Run Docker:

```console
$ docker-compose up
```

* Navigate to [127.0.0.1](127.0.0.1)
* Load Twitter authentication details with the 'Load From Config' button on the [Twitter Authentication page](http://127.0.0.1:8000/twitter_auth).
  * CURRENTLY NOT WORKING -- Additional access tokens can be added via the web interface, requiring a user to log in to Twitter and authorise. 'Export Tokens' can save these tokens to a file for future use.
  * Streams currently need at least 3 tokens added (one for each stream).
* Optional: Log in to the admin interface and add a period task to `update_user_relos_task` daily (alternatively, remove comment from `update_user_relos_periodic` in `tasks.py`)


### Local installation (Mac):

If running without docker, homesite/settings.py should be updated per [this commit](https://github.com/rosscg/crisis-data/tree/3125563d4798ee7a2598da2af8b9c6719219a67b). See related README.md for installation process.

------------
### Data Collection:

The key functionality of the software is tracking keywords and GPS coordinates.
* Edit `config.py` details as needed.
    * The exclusions aim to reduce the amount of processing and noise but affect the sample and therefore need to be considered with respect to the proposed analysis.
* OPTIONAL: Decide on periodic tasks in `tasks.py` (uncomment the decorators to run, uncomment celery beat contained in docker-compose.yml).  
* If media is downloaded (default behaviour), it uses the local directory mapped to /data in the web container -- update DOCKER_WEB_VOLUME in .env before building if required.

* Edit the event name via the 'View Event' page.
* Add keywords. Keywords cannot include spaces.
  * High-priority keywords run as normal, low-priority keywords are saved when the queue is not full. Use this to reduce load.
* Add coordinates for the geo stream.
* Run streams from the 'Stream Status' page. Disable OS auto-sleep.

### Post collection:

* Stop streams, wait for remaining tasks to resolve (could take some time). If there is a queue of tasks, the stream may continue to run until its termination is processed.
* Create a dump of the database (see below). Do this at other relevant milestones.
* Run trim_spam_accounts.
* Run save_user_timelines.
* Run update_relationship_data after a suitable time period (slow process due to rate limits). This currently only supports running once. Running again will damage the data by overwriting the `user_network_update_observed_at` value.
* Run `create_relos_from_list`.
* Optional: Add codes and code Tweets. Database supports up to 9 coders (though UI only supports 2). See section below.
* Export to suitable format for analysis (to be implemented) or access via notebooks.

### Database Dump
Create dump of database:

> ```
> $ docker exec -t crisis-data_db_1 pg_dump -c -U username eventdb | gzip > dump_$(date +"%Y-%m-%d").sql.gz
> ```

Restore db from dump:

> ```
> $ gzip -d -c FILENAME.sql.gz | cat | docker exec -i crisis-data_db_1 psql -U username eventdb
> ```

------------
### Usage - Data Coding:

Once the collection is complete, use the 'Data Coding' interface to code the Tweets. If it has been some time since data collection and you plan to code user objects, it is recommended to run the 'update_screen_names' function, as the source window will not work if the user has changed their screen name since collection.

From the 'Coding Dashboard', add the code dimension (or add a generic name if multiple dimensions are unneeded) then add the codes. From this page, the current code dimension and coder id can be selected before launching the coding interface.

The coding interface link will open three new windows - the top is the main interface. The other two larger windows show the source and either the Tweet feed that occurred during the event (in the case of user coding), or the target of the first URL included in the message (when coding Tweets).
Objects are randomly displayed from a pool of 10 and can be coded either by using the buttons or keyboard.

If selected from the coding dashboard, the secondary coder will be presented with any objects that have been coded by the primary coder. This is intended for coding schema validation purposes. The database supports more than two coders, but require relevant buttons to be implemented on the dash.

The results link will show the proportions distributed to each code, and the disagreement matrix for the two coders.

###### Note:
* Currently only one url from a Tweet is shown in the lower-right window, but in rare cases a Tweet may contain multiple urls.
* If the Tweet (or user) has been deleted and therefore is not displayed in the bottom-left window, the original text content can still be seen by scrolling down in the top interface window.

------------
### Usage - Data Analysis:

The build can host python notebooks which use Django to access models.
* Rebuild using requirements_incl_notebooks.txt
* Uncomment the notebook container in docker-compose.yml
* Open 0.0.0.0:8888 and use the token provided in the console

#### Local Installation
For non-Docker installation, see commit [here](https://github.com/rosscg/crisis-data/tree/3125563d4798ee7a2598da2af8b9c6719219a67b)

------------
### Remote Access:

Use [ngrok](https://ngrok.com/) to serve the site remotely:
`./ngrok http 8000`

Create an account and add your authtoken to avoid 8-hour timeout.

To enable notebooks via ngrok, remote access needs to be enabled:
* Create a config file: `$ jupyter notebook --generate-config`
* Edit the config file by uncommenting the line containing `c.NotebookApp.allow_remote_access` and set to `True`.
* Set a password for the notebook server: `$ jupyter notebook password`
* Run ngrok `./ngrok http 8888`
