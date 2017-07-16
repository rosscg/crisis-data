from django.contrib import admin
from .models import User, Tweet, Hashtag, Url, Relo, Keyword

# Register your models here.
admin.site.register(User)
admin.site.register(Tweet)
admin.site.register(Hashtag)
admin.site.register(Url)
admin.site.register(Relo)
admin.site.register(Keyword)
