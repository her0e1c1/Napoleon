from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User


def get_by_user_id(user_ids):
    if not user_ids:
        return []
    first = user_ids[0]
    q = Q(id=first)
    for i in user_ids[1:]:
        q |= Q(id=i)
    return User.objects.filter(q).all()


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
