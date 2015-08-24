from django.contrib import admin
from django.contrib.auth.models import User
from . import models

# Register your models here.


# class UsersInline(admin.StackedInline):
class UsersInline(admin.TabularInline):
    model = models.Game.players.through


@admin.register(models.Game)
class GameAdmin(admin.ModelAdmin):
    fields = ["label"]
    # list_display = ["label"]
    # list_display_links = ["label"]
    inlines = [UsersInline]
