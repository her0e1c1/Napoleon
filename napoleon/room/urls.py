from django.conf.urls import url
from django.views.generic.edit import CreateView
from django.contrib.auth.forms import UserCreationForm

from . import views

urlpatterns = [
    url(r'^$', views.index, name="top"),
    url(r'^create$', views.create),
    url(r'^login$', views.login),
    url(r'^logout$', views.logout),
    url(r'^signup$', views.signup, name="signup"),
    url(r'^room/(?P<game_id>\d+)$', views.detail),
    url(r'^state/(?P<room_id>\w)', views.game_state),

    # for user
    url(r'^room/(?P<room_id>\w+)/join$', views.join),
    url(r'^room/(?P<room_id>\w+)/quit$', views.quit),
    url(r'^room/(?P<room_id>\w+)/reset$', views.reset),
    # for AI
    url(r'^room/(?P<room_id>\w+)/add$', views.add),

    url(r'^play$', views.play),
]
