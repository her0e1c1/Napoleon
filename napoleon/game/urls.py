from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name="index"),
    url(r'^create$', views.create, name="create"),
    url(r'^detail/(?P<game_id>\d+)$', views.detail, name="detail"),
    # url(r'^json/state/(?P<room_id>\d+)$', views.game_state),
]
