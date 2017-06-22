from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.monitor_user, name='monitor_user'),
    url(r'^submit', views.submit, name='submit'),

    url(r'^view_network$', views.view_network, name='view_network'),
    url(r'^list_users$', views.list_users, name='list_users'),
    url(r'^user/(?P<user_id>\d+)/$', views.user_details, name='user_details'),

    #TODO: Remove these after debugging
    url(r'^stop_stream$', views.stop_stream, name='stop_stream'),
    url(r'^start_stream$', views.start_stream, name='start_stream'),
    url(r'^test$', views.test, name='test'),


    url(r'^network_data_API$', views.network_data_API, name='network_data_API')
]
