from django.shortcuts import render, redirect
from . import models


def index(request):
    if request.method == "POST":
        c = request.POST["content"]
        game = models.Contact(content=c, user=request.user)
        game.save()
        return redirect("top")

    return render(request, "contact.html", {})
