from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.monitor_user, name='monitor_user'),
    url(r'^submit', views.submit, name='submit'),

    url(r'^view_network$', views.view_network, name='view_network'),
    url(r'^view_event$', views.view_event, name='view_event'),
    url(r'^edit_event$', views.edit_event, name='edit_event'),
    url(r'^list_users$', views.list_users, name='list_users'),
    url(r'^user/(?P<user_id>\d+)/$', views.user_details, name='user_details'),
    url(r'^stream_status$', views.stream_status, name='stream_status'),
    url(r'^functions$', views.functions, name='functions'),
    url(r'^coding_interface/(?P<coder>\d)$', views.coding_interface, name='coding_interface'),
    url(r'^coding_interface/submit', views.submit, name='submit'),

    url(r'^callback$', views.callback, name='callback'),
    url(r'^twitter_auth$', views.twitter_auth, name='twitter_auth'),

    url(r'^network_data_API$', views.network_data_API, name='network_data_API')
]
