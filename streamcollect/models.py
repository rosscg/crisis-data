from django.db import models
from django.utils import timezone


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
    #This cannot be the primary_key due to errors with Postgres and BigInt
    user_id = models.BigIntegerField(unique=True)
    utc_offset = models.CharField(max_length=200, null=True)
    verified = models.NullBooleanField(null=True)

    user_class = models.IntegerField()
    added_at = models.DateTimeField()

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
        if self.screen_name is None:
            title = str(self.user_id)
        else:
            title = self.screen_name

        return dict(
            id=str(self.user_id),
            title=title,
            group=str(self.user_class))


class Tweet(models.Model):
    id = models.AutoField(primary_key=True)
    coordinates_lat = models.FloatField(null=True)
    coordinates_long = models.FloatField(null=True)
    coordinates_type = models.CharField(null=True, max_length=10)
    created_at = models.DateTimeField()
    favorite_count = models.IntegerField()
    #filter_level = models.CharField(max_length=10)
    #This cannot be the primary_key due to errors with Postgres and BigInt
    tweet_id = models.BigIntegerField(null=True, unique=True)
    in_reply_to_status_id = models.BigIntegerField(null=True)
    in_reply_to_user_id = models.BigIntegerField(null=True)
    lang = models.CharField(max_length=10, null=True)
    #place                   // see object type, TO BE IMPLEMENTED
    #possibly_sensitive = models.NullBooleanField(null=True)
    quoted_status_id = models.BigIntegerField(null=True)
    #quoted_status = models.ForeignKey('self')           // tweet object
    retweet_count = models.IntegerField()
    #retweeted_status        // tweet object
    source = models.CharField(max_length=300)
    text = models.CharField(max_length=300)
    #user_data               // user object

    author = models.ForeignKey(User, related_name='tweet', on_delete=models.CASCADE)
    data_source = models.IntegerField(default=0) #0 = Added, 1=Low-priority stream, 2=High-priority stream, 3=GPS

    def __str__(self):
        return str(self.text)


class Hashtag(models.Model):
    hashtag = models.CharField(max_length=200, unique=True)
    tweets = models.ManyToManyField(Tweet)

    def __str__(self):
        return str(self.hashtag)


class Url(models.Model):
    url = models.CharField(max_length=400, unique=True)
    tweets = models.ManyToManyField(Tweet)

    def __str__(self):
        return str(self.url)


class Mention(models.Model):
    mention = models.CharField(max_length=200, unique=True)
    tweets = models.ManyToManyField(Tweet)

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


class Keyword(models.Model):
    keyword = models.CharField(max_length = 100, unique=True)
    created_at = models.DateTimeField()
    priority = models.IntegerField(default=0)

    def __str__(self):
        return str(self.keyword)


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


class CeleryTask(models.Model):
    celery_task_id = models.CharField(max_length = 40, unique=True)
    # Use: stream_kw, stream_gps, stream_gps, update_user_relos, trim_spam_accounts, save_twitter_obect
    task_name = models.CharField(max_length=40)
