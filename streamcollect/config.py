# Required ego degree values for an alter account to be considered relevant
REQUIRED_IN_DEGREE = 5
REQUIRED_OUT_DEGREE = 5

# Thresholds for determining spam/celebrity/news accounts (to reject)
FOLLOWERS_THRESHOLD = 5000
FRIENDS_THRESHOLD = 5000
STATUSES_THRESHOLD = 10000

# Ignore Tweets by keyword:
IGNORED_KWS = ['pray']
# Ignore from following sources:
IGNORED_SOURCES = ['Paper.li', 'TweetMyJOBS']
# Ignore Re-Tweets:
IGNORE_RTS = True

# Choose whether to download media from Tweets to hard drive. Saves photos, videos and gifs from Twitter and Instagram posts
DOWNLOAD_MEDIA = True

# Threshold proportion for a hashtag to appear before it is added to tracked tags
TAG_OCCURENCE_THRESHOLD = 0.02
# Threshold proportion for a mentioned user to appear before it is added as user_class=2
MENTION_OCCURENCE_THRESHOLD = 0.01

# Seconds between each keyword stream reset to get fresh keyword list
REFRESH_STREAM = False
STREAM_REFRESH_RATE = 600 # in seconds

# Parameters of bounding box for GPS stream if single point coordinates are provided
BOUNDING_BOX_WIDTH = 1.2
BOUNDING_BOX_HEIGHT = 0.6

# Excludes isolated nodes from network_data_API
EXCLUDE_ISOLATED_NODES = False

# Process a proportion of Tweets in the low-priority keyword stream
STREAM_PROPORTION = 0.06

# Maximum Tweet pins displayed on map (to maintain performance)
MAX_MAP_PINS = 300
