from django.http import JsonResponse
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, redirect, get_object_or_404

from napoleon.game import card
from napoleon.game import session
from napoleon.game.adaptor import RedisAdaptor
from napoleon.AI import ai_names

from . import models
from . import state


def index(request):
    games = models.Room.objects.filter(finished=False).all()
    ctx = {"games": games}
    return render(request, "index.html", ctx)


def _login(request, username, password):
    from django.contrib.auth import login
    user = authenticate(username=username, password=password)
    if user and user.is_active:
        login(request, user)
        return True
    return False


def signup(request):
    if request.method != 'POST':
        return render(request, "signup.html", {"signup_form": UserCreationForm()})

    d = dict(request.POST.items())
    d["password2"] = d.get("password1")
    form = UserCreationForm(d)
    if form.is_valid():
        form.save()
        if _login(request, form.cleaned_data["username"], form.cleaned_data["password1"]):
            return redirect("napoleon.room.views.index")

    return render(request, "signup.html", {"signup_form": form})


@require_http_methods(["POST"])
def login(request):
    username = request.POST.get("username")
    password = request.POST.get("password")
    _login(request, username, password)
    return redirect("napoleon.room.views.index")


@require_http_methods(["POST"])
@login_required
def logout(request):
    from django.contrib.auth import logout
    logout(request)
    return redirect("napoleon.room.views.index")


@require_http_methods(["GET"])
@login_required
def game_state(request, room_id):
    uid = request.user.id
    sid = request.COOKIES["sessionid"]
    s = session.Session(RedisAdaptor(room_id), sid, uid)
    return JsonResponse({"state": s.myself.state.to_json()})


@login_required
def detail(request, game_id):
    room = get_object_or_404(models.Room, pk=game_id)
    return render(request, "detail.html", {
        "room": room,
        "deck": [c.to_json() for c in card.deck],
        "declarations": [d.to_json() for d in card.declarations],
        "ais": ai_names
    })


@require_http_methods(["POST"])
@login_required
def create(request):
    label = request.POST["label"]
    game = models.Room(label=label, user=request.user)
    game.save()
    return redirect("napoleon.room.views.index")


def _get_user_state(request, adaptor):
    uid = request.user.id
    sid = request.COOKIES["sessionid"]
    return state.User(user_id=uid, session_id=sid, adaptor=adaptor)


# Ajax better
@login_required
@require_http_methods(["POST"])
def join(request, room_id):
    _get_user_state(request, adaptor=RedisAdaptor(room_id)).join(request.user)
    return redirect("napoleon.room.views.detail", game_id=room_id)


@login_required
@require_http_methods(["POST"])
def quit(request, room_id):
    _get_user_state(request, adaptor=RedisAdaptor(room_id)).quit()
    return redirect("napoleon.room.views.detail", game_id=room_id)


@login_required
@require_http_methods(["POST"])
def reset(request, room_id):
    _get_user_state(request, adaptor=RedisAdaptor(room_id)).reset()
    return redirect("napoleon.room.views.detail", game_id=room_id)


@login_required
@require_http_methods(["POST"])
def add(request, room_id):
    name = request.POST["name"]
    state.AI(RedisAdaptor(room_id)).add(name)
    return redirect("napoleon.room.views.detail", game_id=room_id)
