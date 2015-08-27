# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Contact',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, verbose_name='ID', serialize=False)),
                ('content', models.TextField()),
                ('created_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(null=True, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
