from django.http import JsonResponse
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, redirect, get_object_or_404

from napoleon import card
from napoleon.game import state
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


def _get_private_game_state(request, room_id):
    session_id = request.COOKIES["sessionid"]
    return state.PrivateGameState(
        user_id=request.user.id,
        session_id=session_id,
        room_id=room_id,
    )


def _get_user_state(request, room_id):
    uid = request.user.id
    sid = request.COOKIES["sessionid"]
    st = _get_private_game_state(request, room_id)
    return state.User(user_id=uid, session_id=sid, state=st)


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
    return JsonResponse({
        "is_valid_session": st.is_valid_session,
        "is_player": st.is_player,
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


@login_required
def detail(request, game_id):
    room = get_object_or_404(models.Room, pk=game_id)
    session_id = request.COOKIES["sessionid"]
    state.reset_session_id_if_changed(game_id, session_id, request.user.id)
    return render(request, "detail.html", {
        "game": room,
        "room": room,
        "deck": [c.to_json() for c in card.deck],
        "declarations": [d.to_json() for d in card.declarations],
    })


@require_http_methods(["POST"])
@login_required
def create(request):
    label = request.POST["label"]
    game = models.Room(label=label, user=request.user)
    game.save()
    return redirect("napoleon.room.views.index")


# Ajax better
@login_required
@require_http_methods(["POST"])
def join(request, room_id):
    _get_user_state(request, room_id).join()
    return redirect("napoleon.room.views.detail", game_id=room_id)


@login_required
@require_http_methods(["POST"])
def quit(request, room_id):
    _get_user_state(request, room_id).quit()
    return redirect("napoleon.room.views.detail", game_id=room_id)


@login_required
@require_http_methods(["POST"])
def reset(request, room_id):
    _get_user_state(request, room_id).reset()
    return redirect("napoleon.room.views.detail", game_id=room_id)
