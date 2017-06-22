from django.db import models
from django.utils import timezone

class User(models.Model):
    created_at = models.DateTimeField(null=True)
    default_profile = models.NullBooleanField(null=True)
    default_profile_image = models.NullBooleanField(null=True)
    description = models.TextField(null=True)
    #TODO entities = NOT YET IMPLEMENTED
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
    profile_background_color = models.CharField(max_length=200, null=True)
    profile_background_image_url = models.CharField(max_length=200, null=True)
    profile_background_image_url_https = models.CharField(max_length=200, null=True)
    profile_background_tile = models.NullBooleanField(null=True)
    profile_image_url = models.CharField(max_length=200, null=True)
    profile_image_url_https = models.CharField(max_length=200, null=True)
    profile_link_color = models.CharField(max_length=200, null=True)
    profile_location = models.CharField(max_length=200, null=True)
    profile_sidebar_border_color = models.CharField(max_length=200,null=True)
    profile_sidebar_fill_color = models.CharField(max_length=200, null=True)
    profile_text_color = models.CharField(max_length=200, null=True)
    profile_use_background_image = models.NullBooleanField(null=True)
    protected = models.NullBooleanField(null=True)
    screen_name = models.CharField(max_length=200, null=True)
    statuses_count = models.IntegerField(null=True)
    suspended = models.NullBooleanField(null=True)
    time_zone = models.CharField(max_length=200, null=True)
    translator_type = models.CharField(max_length=200, null=True)
    url = models.CharField(max_length=200, null=True)
    user_id = models.IntegerField(primary_key=True)
    utc_offset = models.CharField(max_length=200, null=True)
    verified = models.NullBooleanField(null=True)

    user_class = models.IntegerField(default=0)
    added_at = models.DateTimeField(default=timezone.now)
    in_degree = models.IntegerField(default=0)
    out_degree = models.IntegerField(default=0)

    def __str__(self):
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


class Relo(models.Model):
    #TODO: on_delete needs to be resolved appropriately.
    sourceuser = models.ForeignKey(User, related_name='source', on_delete=models.CASCADE)
    targetuser = models.ForeignKey(User, related_name='target', on_delete=models.CASCADE)
    observed_at = models.DateTimeField(default=timezone.now)
    end_observed_at = models.DateTimeField(null=True)

    def as_json(self):
        return dict(
            source=str(self.sourceuser.user_id),
            target=str(self.targetuser.user_id))

    def __str__(self):
        if self.end_observed_at is None:
            return "{} following: {}".format(self.sourceuser, self.targetuser)
        else:
            return "Dead Relo: {} following: {}".format(self.sourceuser, self.targetuser)

class CeleryTask(models.Model):
    celery_task_id = models.CharField(max_length = 40, unique=True)
    # Use: stream_kw, stream_gps, update_user_relos, trim_spam_accounts
    task_name = models.CharField(max_length=40)
