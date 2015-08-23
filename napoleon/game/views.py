from django.core import serializers
from django.http import JsonResponse
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.template.context_processors import csrf
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, redirect, get_object_or_404


from . import models
import card
import state


def index(request):
    games = models.Game.objects.filter(finished=False).all()
    ctx = {"games": games}
    ctx.update(csrf(request))
    return render(request, "index.html", ctx)


def login(request):
    from django.contrib.auth import login
    if request.method == 'POST':
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(username=username, password=password)
        if user and user.is_active:
            login(request, user)
    return render(request, "index.html", {})


# TODO: users in public
@login_required
def user(request):
    # FIXME
    user = serializers.serialize("json", models.User.objects.filter(pk=request.user.id))
    return JsonResponse({"user": user})


def _get_private_game_state(request, room_id):
    session_id = request.COOKIES["sessionid"]
    return state.PrivateGameState(
        user_id=request.user.id,
        session_id=session_id,
        room_id=room_id,
    )


@require_http_methods(["POST"])
@login_required
def join(request, room_id):
    _get_private_game_state(request, room_id).user_id = request.user.id
    return JsonResponse({})


@require_http_methods(["GET"])
@login_required
def private_game_state(request, room_id):
    st = _get_private_game_state(request, room_id)
    d = st.declaration
    return JsonResponse({
        "is_joined": st.is_joined,
        "is_started": st.is_started,
        "is_declared": st.is_declared,
        "is_first_round": st.is_first_round,
        "turn": st.turn,
        "rest": [r.to_json() for r in st.rest],
        "players": st.player_ids,
        "pass_ids": st.pass_ids,
        "napoleon": st.napoleon,
        "hand": [h.to_json() for h in st.hand],
        "declaration": d and int(d),
    })


def detail(request, game_id):
    game = get_object_or_404(models.Game, pk=game_id)
    session_id = request.COOKIES["sessionid"]
    state.reset_session_id_if_changed(game_id, session_id, request.user.id)
    return render(request, "detail.html", {
        "game": game,
        "declarations": [d.to_json() for d in card.declarations],
    })


@require_http_methods(["POST"])
@login_required
def create(request):
    label = request.POST["label"]
    game = models.Game(label=label)
    # TODO: reduce calling save()
    game.save()
    game.users.add(request.user)
    game.save()
    return redirect("game.views.index")
