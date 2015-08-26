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


def _get_private_game_state(request, room_id):
    session_id = request.COOKIES["sessionid"]
    return state.PrivateGameState(
        user_id=request.user.id,
        session_id=session_id,
        room_id=room_id,
    )


@require_http_methods(["GET"])
@login_required
def game_state(request, room_id):
    st = _get_private_game_state(request, room_id)
    d = st.declaration
    a = st.adjutant
    from django.db.models import Q
    q = Q(id=request.user.id)
    for p in st.player_ids:
        q |= Q(id=p)
    users = models.User.objects.filter(q).all()

    # pcards = card.player_cards(st.board, st.player_ids, st.turn)
    return JsonResponse({
        "player_cards": {k: v and v.to_json() for k, v in st.player_cards.items()},
        "player_faces": {k: v for k, v in st.player_faces.items()},
        "did_napoleon_win": st.did_napoleon_win,
        "did_napoleon_lose": st.did_napoleon_lose,
        "users": {u.id: {"name": u.get_username()} for u in users},
        "phase": st.phase,
        "is_finished": st.is_finished,
        "is_joined": st.is_joined,
        "is_appropriate_player_number": st.is_appropriate_player_number,
        "waiting_next_turn": st.waiting_next_turn,
        "turn": st.turn,
        "board": [c.to_json() for c in st.board],
        "player_ids": st.player_ids,
        "pass_ids": st.pass_ids,
        "napoleon": st.napoleon,
        "adjutant": a and a.to_json(),
        "unused": [c.to_json() for c in st.unused],
        "declaration": d and d.to_json(),
        "hand": [h.to_json() for h in st.hand],
        "possible_cards": [int(c) for c in st.possible_cards],
        "role": st.role,
        "rest": [r.to_json() for r in st.rest],
    })


def detail(request, game_id):
    game = get_object_or_404(models.Game, pk=game_id)
    session_id = request.COOKIES["sessionid"]
    state.reset_session_id_if_changed(game_id, session_id, request.user.id)
    return render(request, "detail.html", {
        "game": game,
        "deck": [c.to_json() for c in card.deck],
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
