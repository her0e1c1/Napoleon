from django.contrib import admin
from . import models


@admin.register(models.Contact)
class GameAdmin(admin.ModelAdmin):
    fields = ["content", "user"]
    list_display = fields + ["created_at"]
