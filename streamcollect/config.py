### Data Collection ###

# Choose whether to download media from Tweets to hard drive. Saves photos,
# videos and gifs from Twitter and Instagram posts to protect against deletion
# by the author or Twitter, or profiles made private.
DOWNLOAD_MEDIA = True

# Thresholds for determining spam/celebrity/news accounts
# These may be used to auto-reject to reduce load by adjusting code.
# Currently used for post-collection classification.
FOLLOWERS_THRESHOLD = 5000
FRIENDS_THRESHOLD = 5000
STATUSES_THRESHOLD = 10000

# Ignore Tweets by keyword:
IGNORED_KWS = ['pray', '🙏'] # Chosen based on hurricane study
# Ignore from following sources:
IGNORED_SOURCES = ['Paper.li', 'TweetMyJOBS', 'CareerArc'] # These sources have been identified as automated accounts which do not contribute useful information, so were ignored in the original application of this tool. Adjust as necessary.

# Ignore Re-Tweets. Note that keywords will match phrases in the ancestor Tweet,
# but geo-stream will not detect coordinates in ancestor (nor are RTs ever
# assigned coordinates). Enabling RTs increases load and reduces original content.
IGNORE_RTS = True

# When a streamed Tweet is a reply, this sets how far 'up the chain' to record.
# A high value may create too much load.
MAX_REPLY_DEPTH = 1

# Seconds between each keyword stream reset to get fresh keyword list.
REFRESH_STREAM = False #TODO: No longer needed, remove in twdata
STREAM_REFRESH_RATE = None # in seconds

# Parameters of bounding box for GPS stream if single point coords are provided.
BOUNDING_BOX_WIDTH = 1.2
BOUNDING_BOX_HEIGHT = 0.6

# Threshold proportion for a hashtag to appear before it is added to tracked tags.
TAG_OCCURENCE_THRESHOLD = 0.02
# Threshold proportion for a mentioned user to appear before added as user_class=2
MENTION_OCCURENCE_THRESHOLD = 0.01


### Processing ###

# Required ego degree values for an alter account to be considered relevant
REQUIRED_IN_DEGREE = 5
REQUIRED_OUT_DEGREE = 5

# Excludes isolated nodes from network_data_API
EXCLUDE_ISOLATED_NODES = False



### Visualisation: ###

# Maximum Tweet pins displayed on map (to maintain performance)
MAX_MAP_PINS = 300
