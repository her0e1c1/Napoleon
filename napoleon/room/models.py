from django.db import models
from django.contrib.auth.models import User


class Room(models.Model):
    label = models.CharField(max_length=200, blank=False)
    waiting = models.BooleanField(default=True, null=False)
    finished = models.BooleanField(default=False, null=False)
    created_at = models.DateTimeField(auto_now=True, null=False)
    user = models.ForeignKey(User, null=False)

    def __str__(self):
        return "%s" % self.label

    def __unicode__(self):
        return "%s" % self.label


class Player(models.Model):
    pass
