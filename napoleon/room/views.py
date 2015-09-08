from django.http import JsonResponse
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, redirect, get_object_or_404

from napoleon.game import card
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


def _get_game_state(request, room_id):
    uid = request.user.id
    sid = request.COOKIES["sessionid"]
    return state.GameStateWithSession(room_id=room_id, user_id=uid, session_id=sid)


def _get_user_state(request, room_id):
    uid = request.user.id
    sid = request.COOKIES["sessionid"]
    sta = _get_game_state(request, room_id)
    return state.User(user_id=uid, session_id=sid, state=sta)


def _get_myself(request, room_id):
    sid = request.COOKIES["sessionid"]
    st = state.GameState(room_id)
    return state.Myself(session_id=sid, state=st)


@require_http_methods(["GET"])
@login_required
def game_state(request, room_id):
    from django.db.models import Q
    q = Q(id=request.user.id)
    s = _get_game_state(request, room_id)
    for p in s.players:
        q |= Q(id=p.user_id)
    users = models.User.objects.filter(q).all()
    d = s.declaration
    a = s.adjutant
    jj = s.to_json()
    try:
        myself = _get_myself(request, room_id)
    except state.InvalidSession:
        myself = state.Player(user_id=request.user.id, state=state.GameState(room_id))
        myself.is_valid = False

    cxt = {
        # "is_valid_session": st.is_valid_session,
        # "is_player": st.is_player,
        "player_cards": {k: v and v.to_json() for k, v in s.player_cards.items()},
        "number_of_player_hand": s.number_of_player_hand,
        "player_faces": s.player_faces,
        # "did_napoleon_win": st.did_napoleon_win,
        # "did_napoleon_lose": st.did_napoleon_lose,
        "users": {u.id: {"name": u.get_username()} for u in users},
        "phase": s.phase,
        # "is_finished": st.is_finished,
        # "is_joined": st.is_joined,
        "is_appropriate_player_number": s._phase.is_appropriate_player_number,
        "waiting_next_turn": s._phase.waiting_next_turn,
        "turn": s.turn.user_id,
        "board": [c.to_json() for c in s.board],
        "player_ids": [p.user_id for p in s.players],
        "pass_ids": [p.user_id for p in s.passed_players],
        "napoleon": s.napoleon,
        "adjutant": a and a.to_json(),
        "unused": [c.to_json() for c in s.unused_faces],
        "declaration": d and d.to_json(),
    }

    myself = _get_myself(request, room_id)
    if myself:
        cxt.update({
            "hand": [c.to_json() for c in myself.hand],
            "role": myself.role and myself.role.value,
            "possible_cards": [int(c) for c in myself.possible_cards],
            "rest": s.rest and [r.to_json() for r in s.rest],
        })

    return JsonResponse(cxt)


@login_required
def detail(request, game_id):
    room = get_object_or_404(models.Room, pk=game_id)
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
