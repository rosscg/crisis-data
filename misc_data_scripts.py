# Don't run this as a script - paste code as needed.

# These snippets are primarily used to remove Tweets which are unwanted.
# Original use was to remove tweets with 'pray' and their associated users/entities.

# Find tweets with a duplicate tweet_id and delete the newest

from django.db.models import Count
from streamcollect.models import Tweet
from streamcollect.models import User

dupes = Tweet.objects.values('tweet_id').annotate(Count('id')).order_by().filter(id__count__gt=1)

ids = dupes.values('tweet_id')

for id in ids:
     tweets = Tweet.objects.filter(tweet_id=id.get('tweet_id'))
     if tweets.count() == 2:
             id1 = tweets[0].id
             id2 = tweets[1].id
             if id1 > id2:
                     delete_id = id1
             else:
                     delete_id = id2
             Tweet.objects.filter(id=delete_id).delete()

#-----------------#

# Remove 'prayer' tweets (then need to check for isolated users/tags etc as above)
t = Tweet.objects.filter(text__icontains='pray').delete()
#t = Tweet.objects.filter(data_source__gte=1).filter(text__icontains='pray').delete()

#-----------------#

# Delete hashtags that are now not linked to any Tweets.
# Adjust and repeat for Mention and Url.
# This isn't necessary after deleting duplicates, as the remaining one links.

from streamcollect.models import Hashtag
count=0
items = Hashtag.objects.all()
for i in items:
    if i.tweets.all().count() == 0:
        print('count = 0 for hashtag {}'.format(i.hashtag))
        count += 1
        i.delete()
        # Uncomment to only count hashtags including 'pray'
        #if 'pray' in h.hashtag:
        #    print(h.hashtag)
        #else:
        #    count -= 1
print(count)

#-----------------#
# Remove/demote class 2 users who now don't belong to any tweets.

users = User.objects.filter(user_class=2).filter(tweet=None)
#Note that 'tweet=None' should be 'author=None' in old version, same for relo names
for u in users:
    class2 = False
    for r in u.relo_in.all(): # Incoming relo, previously 'target'
        if r.source_user.user_class == 2:
            print('user has incoming link: {}'.format(r.source_user.screen_name))
            r.source_user.out_degree -= 1
            r.source_user.save()
            class2 = True
    for r in u.relo_out.all(): # Outgoing relo, previously 'source'
        if r.target_user.user_class == 2:
            print('user has outgoing link: {}'.format(r.target_user.screen_name))
            r.target_user.in_degree -= 1
            r.target_user.save()
            class2 = True
    if class2 is False:
        print('Deleting user.')
        u.relo_out.all().delete() # Changed
        u.relo_in.all().delete() # Changed
        #Check all relos, see if isolated and delete if necessary
        u.delete()
        pass
    else:
        print('Demoting user.')
        r_out = u.relo_out.all() # Changed
        for r in r_out:
            if r.target_user.user_class < 2:
                r.delete()
        r_in = u.relo_in.all() # Changed
        for r in r_in:
            if r.source_user.user_class < 2:
                r.delete()
        u.user_class = 0
        u.save()

#-----------------#
# Remove alter User objects which are no longer linked to anyone.

lone_users = User.objects.filter(user_class=0).filter(relo_out=None, relo_in=None) #previously source and target
lone_users.count()
lone_users.delete()

#-----------------#
# Finding earliest and latest dates of Tweets for each class

for i in range(4):
    early = None
    late = None
    tweets = Tweet.objects.filter(data_source=i)
    for t in tweets:
        if early is None or t.created_at < early:
            early = t.created_at
        if late is None or t.created_at > late:
            late = t.created_at
    print("Earliest for {}: {}".format(i, early))
    print("Latest for {}: {}".format(i, late))


#-----------------#
#Dealing with old Databases
#-----------------#
# # Moving streamed column into data_source column
# #Add temp data_source column in SQL:
# \d+ streamcollect_tweet #View column names
# ALTER TABLE streamcollect_tweet ADD COLUMN data_source2 int;
# UPDATE streamcollect_tweet SET data_source2 = CASE WHEN streamed='f' THEN 0 ELSE 1 END;
# SELECT id, streamed, data_source2 FROM streamcollect_tweet;
#
# # After performing migrations:
# UPDATE streamcollect_tweet SET data_source2 = data_source;
# ALTER TABLE streamcollect_tweet DROP COLUMN data_source2;

# Checking if tweet is within GPS bounding box and updating data_source accordingly (for old databases without data_source column)

gps = [-99.9590682, 26.5486063, -93.9790001, 30.3893434] # Long, lat, long, lat
ts = Tweet.objects.filter(coordinates_lon__isnull=False)

for t in ts:
    if t.coordinates_lat > gps[1] and t.coordinates_lat < gps[3]:
          if t.coordinates_lon > gps[0] and t.coordinates_lon < gps[2]:
              t.data_source = 3
              t.save()
              u = t.author
              u.data_source = 3
              u.save()

#-----------------#






#-----------------#
#-----------------#
# Exporting Tweet dates to file to view on graph

filename = 'irma_date_data_{}.csv' # Change as needed

for i in range(4):
    tweets = Tweet.objects.filter(data_source=i)
    datafile = open(filename.format(i), 'w')
    for t in tweets:
        datafile.write(str(t.created_at)+'\n')
    datafile.close()



#-----------------#
# View histogram of dates (in new VEnv)

#    # Set up environment
#    python3 -m venv venv
#    source venv/bin/activate
#    pip3 install pandas
#    pip3 install jupyter
#    jupyter notebook

%matplotlib inline
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt

filename = 'irma_date_data_{}.csv' # Change as needed

data_frames = {}
for i in range(4): # 4 classes of Tweet data_source
    try:
        df = pd.read_csv(filename.format(i), header=None)
    except:
        continue
    df[0] = pd.to_datetime(df[0])
    data_frames["data_file_{}".format(i)] = df

for i in data_frames:
    df = data_frames.get(i)
    data = df.groupby([df[0].dt.day, df[0].dt.hour]).count()
    data.plot(title='Tweet data_source = {}'.format(i[len(i)-1:]), legend=False)



# To plot on same graph (Seems to break x scale)
ax = None
for i in data_frames:
    df = data_frames.get(i)
    data = df.groupby([df[0].dt.day, df[0].dt.hour]).count()

    ax = data.plot(title='Tweet data_source = {}'.format(i[len(i)-1:]), legend=False, ax=ax)

    #if ax is None:
    #    ax = data.plot(title='Tweet data_source = {}'.format(i[len(i)-1:]), legend=False)
    #else:
    #    data.plot(title='Tweet data_source = {}'.format(i[len(i)-1:]), legend=False, ax=ax)
