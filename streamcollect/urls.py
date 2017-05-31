from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.monitor_user, name='monitor_user'),
    url(r'^submit', views.submit, name='submit'),

    url(r'^view_network$', views.view_network, name='view_network'),
    url(r'^list_users$', views.list_users, name='list_users'),
    url(r'^user/(?P<user_id>\d+)/$', views.user_details, name='user_details'),

    url(r'^delete_today$', views.delete_today, name='delete_today'),


    url(r'^network_data_API$', views.network_data_API, name='network_data_API')
]
