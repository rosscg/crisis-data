from django.db import models
from django.utils import timezone

class User(models.Model):
    contributors_enabled = models.BooleanField()
    created_at = models.DateTimeField(blank=True, null=True)
    default_profile = models.BooleanField()
    default_profile_image = models.BooleanField()
    description = models.TextField()
    #TODO entities = NOT YET IMPLEMENTED
    favourites_count = models.IntegerField()
    followers_count = models.IntegerField()
    friends_count = models.IntegerField()
    geo_enabled = models.BooleanField()
    has_extended_profile = models.BooleanField()
    id_str = models.CharField(primary_key=True,max_length=200)
    is_translation_enabled = models.BooleanField()
    is_translator = models.BooleanField()
    lang = models.CharField(max_length=200)
    listed_count = models.IntegerField()
    location = models.CharField(max_length=200)
    name = models.CharField(max_length=200)
    needs_phone_verification = models.BooleanField()
    notifications = models.BooleanField()
    profile_background_color = models.CharField(max_length=200)
    profile_background_image_url = models.CharField(max_length=200)
    profile_background_image_url_https = models.CharField(max_length=200)
    profile_background_tile = models.BooleanField()
    profile_image_url = models.CharField(max_length=200)
    profile_image_url_https = models.CharField(max_length=200)
    profile_link_color = models.CharField(max_length=200)
    profile_location = models.CharField(max_length=200, null=True)
    profile_sidebar_border_color = models.CharField(max_length=200)
    profile_sidebar_fill_color = models.CharField(max_length=200)
    profile_text_color = models.CharField(max_length=200)
    profile_use_background_image = models.BooleanField()
    protected = models.BooleanField()
    screen_name = models.CharField(max_length=200)
    statuses_count = models.IntegerField()
    suspended = models.BooleanField()
    time_zone = models.CharField(max_length=200, null=True)
    translator_type = models.CharField(max_length=200)
    url = models.CharField(max_length=200, null=True)
    utc_offset = models.CharField(max_length=200, null=True)
    verified = models.BooleanField()

    added_on = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.screen_name
