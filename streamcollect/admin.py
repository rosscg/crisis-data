from django.contrib import admin
from .models import Event, GeoPoint, User, Tweet, Hashtag, Url, Relo, Keyword, ConsumerKey, AccessToken, Mention

# Register your models here.
admin.site.register(Event)
admin.site.register(GeoPoint)
admin.site.register(User)
admin.site.register(Tweet)
admin.site.register(Hashtag)
admin.site.register(Url)
admin.site.register(Relo)
admin.site.register(Keyword)
admin.site.register(ConsumerKey)
admin.site.register(AccessToken)
admin.site.register(Mention)
