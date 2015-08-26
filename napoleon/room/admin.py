from django.contrib import admin
from . import models

# Register your models here.


# class UsersInline(admin.StackedInline):
# class UsersInline(admin.TabularInline):
#     model = models.Room.user.through


@admin.register(models.Room)
class GameAdmin(admin.ModelAdmin):
    fields = ["label"]
    # list_display = ["label"]
    # list_display_links = ["label"]
    # inlines = [UsersInline]
