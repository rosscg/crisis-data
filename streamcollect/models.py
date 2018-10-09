from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.postgres.fields import ArrayField


class Event(models.Model):
    name = models.CharField(max_length=20)
    time_start = models.DateTimeField(null=True, blank=True)
    time_end = models.DateTimeField(null=True, blank=True)
    kw_stream_start = models.DateTimeField(null=True, blank=True)
    kw_stream_end = models.DateTimeField(null=True, blank=True)
    gps_stream_start = models.DateTimeField(null=True, blank=True)
    gps_stream_end = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if Event.objects.exists() and not self.pk:
            raise ValidationError('There can be only one Event instance')

        if self.time_end and self.time_start and self.time_start >= self.time_end:
            print('Error, dates not in order')
            self.time_end = None

        self.name = self.name.replace(' ', '-')

        return super(Event, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.name)


class GeoPoint(models.Model):
    event = models.ForeignKey(Event, related_name='geopoint', on_delete=models.CASCADE, null=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if GeoPoint.objects.all().count() >= 2 and not self.pk:
            raise ValidationError('There can be only two GeoPoint instances')
        if self.latitude is None or self.longitude is None: # Delete if field left blank
            try:
                self.delete()
            except:
                pass
            return
        if self.longitude is not None:
            if self.longitude < -180 or self.longitude > 180: # prevents values from 'scrolling around map'
                return
        if self.latitude is not None:
            if self.latitude < -90 or self.latitude > 90: # prevents values from 'scrolling around map'
                return
        self.event = Event.objects.all()[0]
        return super(GeoPoint, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.latitude) + ", " + str(self.longitude)


class Keyword(models.Model):
    event = models.ForeignKey(Event, related_name='keyword', on_delete=models.CASCADE, null=True)
    keyword = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField()
    priority = models.IntegerField(default=0)

    def save(self, *args, **kwargs):

        self.keyword = self.keyword.replace(' ', '') # Twitter expects single keywords

        try:
            self.event = Event.objects.all()[0]
        except:
            print("ERROR adding keyword - create event first")
            return
        return super(Keyword, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.keyword)



class Place(models.Model):
    id = models.AutoField(primary_key=True)
    place_id = models.CharField(max_length=20, null=False, unique=True)
    url = models.CharField(max_length=200, null=True)   # TODO: These fields are only null to make get_or_create faster, which may have no effect.
    place_type = models.CharField(max_length=100, null=True)
    name = models.CharField(max_length=100, null=True)
    full_name = models.CharField(max_length=100, null=True)
    country_code = models.CharField(max_length=5, null=True)
    country = models.CharField(max_length=100, null=True)

    #TODO: Consider making these Geepoint objects and fix GeoPoint spec.
    #TODO: Check if boxes are ever non-rectangle (and therefore need all 4 points)
    lat_1 = models.FloatField(null=True)
    lon_1 = models.FloatField(null=True)
    lat_2 = models.FloatField(null=True)
    lon_2 = models.FloatField(null=True)
    lat_3 = models.FloatField(null=True)
    lon_3 = models.FloatField(null=True)
    lat_4 = models.FloatField(null=True)
    lon_4 = models.FloatField(null=True)

    def get_midpoint(self):
        lat = round((self.lat_1 + self.lat_2 + self.lat_3 + self.lat_4)/4, 5)
        lon = round((self.lon_1 + self.lon_2 + self.lon_3 + self.lon_4)/4, 5)
        return [lat, lon]


    def __str__(self):
        try:
            c = self.get_midpoint()
            return "Place: {}, middle coords lat: {}, lon: {}".format(self.full_name, c[0], c[1])
        except:
            return "Place id: {}".format(self.place_id)


class User(models.Model):
    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(null=True)
    default_profile = models.NullBooleanField(null=True)
    default_profile_image = models.NullBooleanField(null=True)
    description = models.TextField(null=True)
    #TODO entities = NOT YET IMPLEMENTED - refers to URLs in profile and description
    favourites_count = models.IntegerField(null=True)
    followers_count = models.IntegerField(null=True)
    friends_count = models.IntegerField(null=True)
    geo_enabled = models.NullBooleanField(null=True)
    has_extended_profile = models.NullBooleanField(null=True)
    is_translation_enabled = models.NullBooleanField(null=True)
    lang = models.CharField(max_length=200, null=True)
    listed_count = models.IntegerField(null=True)
    location = models.CharField(max_length=200, null=True)
    name = models.CharField(max_length=200, null=True)
    needs_phone_verification = models.NullBooleanField(null=True)
    #profile_background_color = models.CharField(max_length=200, null=True)
    #profile_background_image_url = models.CharField(max_length=200, null=True)
    #profile_background_image_url_https = models.CharField(max_length=200, null=True)
    #profile_background_tile = models.NullBooleanField(null=True)
    #profile_image_url = models.CharField(max_length=200, null=True)
    #profile_image_url_https = models.CharField(max_length=200, null=True)
    #profile_link_color = models.CharField(max_length=200, null=True)
    #profile_location = models.CharField(max_length=200, null=True)
    #profile_sidebar_border_color = models.CharField(max_length=200,null=True)
    #profile_sidebar_fill_color = models.CharField(max_length=200, null=True)
    #profile_text_color = models.CharField(max_length=200, null=True)
    #profile_use_background_image = models.NullBooleanField(null=True)
    protected = models.NullBooleanField(null=True)
    screen_name = models.CharField(max_length=200, null=True)
    statuses_count = models.IntegerField(null=True)
    suspended = models.NullBooleanField(null=True)
    time_zone = models.CharField(max_length=200, null=True)
    translator_type = models.CharField(max_length=200, null=True)
    url = models.CharField(max_length=200, null=True)
    user_id = models.BigIntegerField(unique=True) # This cannot be the primary_key due to errors with Postgres and BigInt
    utc_offset = models.CharField(max_length=200, null=True)
    verified = models.NullBooleanField(null=True)

    user_class = models.IntegerField()
    added_at = models.DateTimeField()
    data_source = models.IntegerField(default=0) # 0=Added, 1=Low-priority stream, 2=High-priority stream, 3=GPS
    old_screen_name = models.CharField(max_length=200, null=True) # Originally observed screen_name if since-changed.
    is_deleted = models.NullBooleanField(null=True) # True where profile is detected as deleted (or protected? TODO: check) in update method.
    is_deleted_observed = models.DateTimeField(null=True)

    user_following = ArrayField(models.BigIntegerField(), null=True) #   TODO: Testing temporarily storing as list rather than creating relo objects.
    user_followers = ArrayField(models.BigIntegerField(), null=True) #   TODO: Testing

    user_following_update = ArrayField(models.BigIntegerField(), null=True) #   TODO: Testing temporarily
    user_followers_update = ArrayField(models.BigIntegerField(), null=True) #   TODO: Testing
    user_network_update_observed_at = models.DateTimeField(null=True) #   TODO: Testing

    # These currently represent the degrees to ego accounts and therefore only
    # relevant to alter objects, or egos with relationships with other egos.
    in_degree = models.IntegerField(default=0)
    out_degree = models.IntegerField(default=0)

    def __str__(self):
        if self.screen_name:
            return self.screen_name
        else:
            return str(self.user_id)

    def as_json(self):
        # Calculate the best (lowest) coded tweet for a user
        # TODO: Remove this or place it elsewhere.
        best_code = ''
        for t in self.tweet.all():
            for c in t.coding_for_tweet.all():
                if (best_code == '' or c.data_code.data_code_id < best_code) and c.data_code.data_code_id > 0:
                    best_code = c.data_code.data_code_id
        if self.screen_name is None:
            title = str(self.user_id)
        else:
            title = self.screen_name
        return dict(
            id=str(self.user_id),
            title=title,
            user_class=str(self.user_class),
            group=str(best_code))


class Tweet(models.Model):
    id = models.AutoField(primary_key=True)
    coordinates_lat = models.FloatField(null=True)
    coordinates_lon = models.FloatField(null=True)
    coordinates_type = models.CharField(null=True, max_length=10)
    created_at = models.DateTimeField()
    favorite_count = models.IntegerField()               # This will likely always be zero for Tweets from stream.
    #filter_level = models.CharField(max_length=10)
    tweet_id = models.BigIntegerField(null=True, unique=True)   #This cannot be the primary_key due to errors with Postgres and BigInt
    in_reply_to_status_id = models.BigIntegerField(null=True)
    in_reply_to_user_id = models.BigIntegerField(null=True)
    lang = models.CharField(max_length=10, null=True)
    #possibly_sensitive = models.NullBooleanField(null=True)
    quoted_status_id_int = models.BigIntegerField(null=True)
    retweet_count = models.IntegerField()               # This will likely always be zero for Tweets from stream.
    #retweeted_status        // tweet object
    source = models.CharField(max_length=300)
    text = models.CharField(max_length=500)

    author = models.ForeignKey(User, related_name='tweet', on_delete=models.CASCADE)
    place = models.ForeignKey(Place, related_name='tweet', on_delete=models.SET_NULL, null=True)
    data_source = models.IntegerField(default=0) #0 = Added, 1=Low-priority stream, 2=High-priority stream, 3=GPS
    is_deleted = models.NullBooleanField(null=True) # True where profile is detected as deleted (or protected? TODO: check) in update method.
    is_deleted_observed = models.DateTimeField(null=True)
    media_files = ArrayField(models.CharField(max_length=200), null=True)
    media_files_type = models.CharField(max_length=200, null=True) # describes the media_files field: image, video or gif

    replied_to_status = models.ForeignKey('self', related_name='replied_by', on_delete=models.SET_NULL, null=True)
    quoted_status = models.ForeignKey('self', related_name='quoted_by', on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return str(self.text)

    def as_dict(self):
        if self.coordinates_lat is None and self.place is not None:
            midpoint = self.place.get_midpoint()
            lat = midpoint[0]
            lon = midpoint[1]
        else:
            lat = self.coordinates_lat
            lon = self.coordinates_lon

        return dict(
            text = self.text,
            author = self.author.screen_name,
            tweet_id = str(self.tweet_id), # Passed as string due to javascript |safe tag appears to round to nearest 100
            lat = lat,
            lon = lon,
            data_source = self.data_source
            )


class DataCodeDimension(models.Model):
    name = models.CharField(max_length=20, null=False)
    description = models.CharField(null=True, max_length=400)
    coding_subject = models.CharField(max_length=20, null=False)

    def save(self, *args, **kwargs):
        if self.coding_subject == 'user' or self.coding_subject == 'tweet' :
            return super(DataCodeDimension, self).save(*args, **kwargs)
        else:
            print('Error with coding subject label: \'{}\'. Must be \'tweet\' or \'user\'.'.format(self.coding_subject))
            return

    def __str__(self):
        return str(self.name)


class DataCode(models.Model):
    data_code_id = models.IntegerField(unique=True, null=False) # Required as the PK doesn't reset when rows are removed. #TODO: May not be required anymore
    name = models.CharField(max_length=40, null=False)
    description = models.CharField(null=True, max_length=400)
    tweets = models.ManyToManyField(Tweet, through='Coding')
    users = models.ManyToManyField(User, through='Coding')
    dimension = models.ForeignKey(DataCodeDimension, related_name='datacode', on_delete=models.CASCADE, null=True)

    def __str__(self):
        return "Code ID {}: {}, Dimension: {}".format(str(self.data_code_id), self.name, self.dimension)


class Coding(models.Model):
    # TODO: Write validation to allow only one FK here? - either tweet OR user.
    tweet = models.ForeignKey(Tweet, related_name='coding_for_tweet', on_delete=models.CASCADE, null=True)
    user = models.ForeignKey(User, related_name='coding_for_user', on_delete=models.CASCADE, null=True)
    data_code = models.ForeignKey(DataCode, on_delete=models.CASCADE)
    coding_id = models.IntegerField(default=1)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('coding_id', 'data_code', 'tweet')
        unique_together = ('coding_id', 'data_code', 'user')

    def __str__(self):
        if self.tweet is not None:
            return "DataCode: {}, Tweet: {}, Coder: {}".format(str(self.data_code.data_code_id), self.tweet.text[:40], str(self.coding_id))
        else:
            return "DataCode: {}, User ID: {}, Coder: {}".format(str(self.data_code.data_code_id), self.user.screen_name, str(self.coding_id))


class Hashtag(models.Model):
    hashtag = models.CharField(max_length=200, unique=True)
    tweets = models.ManyToManyField(Tweet, related_name='hashtags')

    def __str__(self):
        return str(self.hashtag)


class Url(models.Model):
    url = models.CharField(max_length=400, unique=True)
    tweets = models.ManyToManyField(Tweet, related_name='urls')

    def __str__(self):
        return str(self.url)


class Mention(models.Model):
    mention = models.CharField(max_length=200, unique=True)
    tweets = models.ManyToManyField(Tweet, related_name='mentions')

    def __str__(self):
        return str(self.mention)


class Relo(models.Model):
    #TODO: on_delete needs to be resolved appropriately.
    source_user = models.ForeignKey(User, related_name='relo_out', on_delete=models.CASCADE)
    target_user = models.ForeignKey(User, related_name='relo_in', on_delete=models.CASCADE)
    observed_at = models.DateTimeField()
    end_observed_at = models.DateTimeField(null=True)

    def as_json(self):
        return dict(
            source=str(self.source_user.user_id),
            target=str(self.target_user.user_id))

    def as_csv(self):
        return '{},{}'.format(self.source_user.user_id, self.target_user.user_id)

    def __str__(self):
        if self.end_observed_at is None:
            return "{} following: {}".format(self.source_user, self.target_user)
        else:
            return "Dead Relo: {} following: {}".format(self.source_user, self.target_user)


class AccessToken(models.Model):
    access_key = models.CharField(max_length=100, unique=True)
    access_secret = models.CharField(max_length=100, unique=True)
    screen_name = models.CharField(max_length=40, unique=True, null=True)

    def __str__(self):
        return "(\'{}\', \'{}\', \'{}\')".format(self.screen_name, self.access_key, self.access_secret)


class ConsumerKey(models.Model):
    consumer_key = models.CharField(max_length=100, unique=True)
    consumer_secret = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return "(\'{}\', \'{}\')".format(self.consumer_key, self.consumer_secret)


#class CeleryTask(models.Model):
#    celery_task_id = models.CharField(max_length = 40, unique=True)
    # Use: stream_kw_high, stream_kw_low, stream_gps, stream_gps, update_user_relos, trim_spam_accounts, save_twitter_obect
#    task_name = models.CharField(max_length=40)
