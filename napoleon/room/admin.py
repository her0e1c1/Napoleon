from django.contrib import admin
from . import models


@admin.register(models.Room)
class GameAdmin(admin.ModelAdmin):
    fields = ["label"]
