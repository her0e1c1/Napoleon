from django.db import models
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session


def get_user(session_key):
    try:
        session = Session.objects.get(session_key=session_key)
        uid = session.get_decoded().get('_auth_user_id')
        return User.objects.get(pk=uid)
    except (Session.DoesNotExist, User.DoesNotExist):
        return None


# Roomに変更する
class Game(models.Model):
    label = models.CharField(max_length=200, blank=False)
    waiting = models.BooleanField(default=True, null=False)
    finished = models.BooleanField(default=False, null=False)
    created_at = models.DateTimeField(auto_now=True, null=False)
    players = models.ManyToManyField(User, related_name="games")

    def __str__(self):
        return "%s" % self.label

    def __unicode__(self):
        return "%s" % self.label


class Player(models.Model):
    user = models.OneToOneField(User, unique=True)
    games = models.ManyToManyField(Game)
