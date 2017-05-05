from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.monitor_user, name='monitor_user'),
    url(r'^submit', views.submit, name='submit'),


    url(r'^view_network$', views.view_network, name='view_network'),
    url(r'^show_user$', views.show_user, name='show_user'),
    url(r'^network_data_API$', views.network_data_API, name='network_data_API')
]
