from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index),
    url(r'^create$', views.create),
    url(r'^room/(?P<game_id>\d+)$', views.detail),
    url(r'^state/(?P<room_id>\d+)$', views.game_state),
]
