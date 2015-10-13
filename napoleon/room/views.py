from django.http import JsonResponse
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, redirect, get_object_or_404

from napoleon.game import card
from napoleon.game import state
from napoleon.game import session
from napoleon.game.adaptor import RedisAdaptor
from napoleon.AI import ai_names
from . import models


def index(request):
    games = models.Room.objects.filter(finished=False).all()
    ctx = {"games": games}
    return render(request, "index.html", ctx)


@require_http_methods(["POST"])
def login(request):
    from django.contrib.auth import login
    username = request.POST["username"]
    password = request.POST["password"]
    user = authenticate(username=username, password=password)
    if user and user.is_active:
        login(request, user)
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
    sid = request.COOKIES["sessionid"]
    adaptor = RedisAdaptor(room_id)
    player = state.Player(
        user_id=request.user.id,
        state=state.GameState(adaptor, session.Session(adaptor, sid))
    )
    return JsonResponse({"state": player.state.to_json()})


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
