from django.db import models
from django.contrib.auth.models import User


class Contact(models.Model):
    content = models.TextField(blank=False)
    created_at = models.DateTimeField(auto_now=True, null=False)
    user = models.ForeignKey(User, null=True)
