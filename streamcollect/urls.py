from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.monitor_user, name='monitor_user'),

    url(r'^submit', views.submit, name='submit')
]
