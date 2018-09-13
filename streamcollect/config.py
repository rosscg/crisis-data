### Data Collection ###

# Choose whether to download media from Tweets to hard drive. Saves photos, videos and gifs from Twitter and Instagram posts to protect against deletion by the author.
DOWNLOAD_MEDIA = True

# Process a proportion of Tweets in the low-priority keyword stream. This must be manually adjusted to match the systems limits.
#STREAM_PROPORTION = 0.50

# Thresholds for determining spam/celebrity/news accounts (to reject)
FOLLOWERS_THRESHOLD = 5000
FRIENDS_THRESHOLD = 5000
STATUSES_THRESHOLD = 10000

# Ignore Tweets by keyword:
IGNORED_KWS = ['pray', '🙏']
# Ignore from following sources:
IGNORED_SOURCES = ['Paper.li', 'TweetMyJOBS', 'CareerArc']

# Ignore Re-Tweets. Note that keywords will match phrases in the ancestor Tweet, but geo-stream
# will not detect coordinates in ancestor (nor are RTs ever assigned coordinates). Enabling RTs
# requires more efficient handling to be implemented.
IGNORE_RTS = True

# When a streamed Tweet is a reply, this sets how far 'up the chain' to record. A high value may create too much load.
MAX_REPLY_DEPTH = 1

# Seconds between each keyword stream reset to get fresh keyword list.
REFRESH_STREAM = False #TODO: No longer needed, remove in twdata
STREAM_REFRESH_RATE = None # in seconds

# Parameters of bounding box for GPS stream if single point coordinates are provided.
BOUNDING_BOX_WIDTH = 1.2
BOUNDING_BOX_HEIGHT = 0.6

# Threshold proportion for a hashtag to appear before it is added to tracked tags.
TAG_OCCURENCE_THRESHOLD = 0.02
# Threshold proportion for a mentioned user to appear before it is added as user_class=2
MENTION_OCCURENCE_THRESHOLD = 0.01

# Number of tasks to run during data collection (up to three for streams, rest for saving Tweet data), should be set to number of cores on machine. If a different number is used, celery should run with the same value for --concurrency (> $ celery -A homesite worker --concurrency=4 -l info -Ofair)
CONCURRENT_TASKS = 4


### Processing ###

# Required ego degree values for an alter account to be considered relevant
REQUIRED_IN_DEGREE = 5
REQUIRED_OUT_DEGREE = 5

# Excludes isolated nodes from network_data_API
EXCLUDE_ISOLATED_NODES = False



### Visualisation: ###

# Maximum Tweet pins displayed on map (to maintain performance)
MAX_MAP_PINS = 300
