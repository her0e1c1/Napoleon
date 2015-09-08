from django.conf.urls import url
from django.views.generic.edit import CreateView
from django.contrib.auth.forms import UserCreationForm

from . import views

urlpatterns = [
    url(r'^$', views.index, name="top"),
    url(r'^create$', views.create),
    url(r'^login$', views.login),
    url(r'^logout$', views.logout),
    url(r'^signup$', CreateView.as_view(
        template_name="signup.html",
        form_class=UserCreationForm,
        success_url="/",
    ), name="signup"),
    url(r'^room/(?P<game_id>\d+)$', views.detail),
    url(r'^room/(?P<room_id>\d+)/join$', views.join),
    url(r'^room/(?P<room_id>\d+)/quit$', views.quit),
    url(r'^room/(?P<room_id>\d+)/reset$', views.reset),
    url(r'^state/(?P<room_id>\d+)$', views.game_state),
]
