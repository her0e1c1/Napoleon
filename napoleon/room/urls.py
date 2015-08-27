from django.conf.urls import url
from django.conf.urls import include
from django.views.generic.edit import CreateView
from django.contrib.auth.forms import UserCreationForm

from . import views

urlpatterns = [
    url(r'^$', views.index),
    url(r'^create$', views.create),
    url(r'^login$', views.login),
    url(r'^logout$', views.logout),
    url(r'^signup$', CreateView.as_view(
        template_name="signup.html",
        form_class=UserCreationForm,
        success_url="/",
    ), name="signup"),
    url(r'^room/(?P<game_id>\d+)$', views.detail),
    url(r'^state/(?P<room_id>\d+)$', views.game_state),
]
