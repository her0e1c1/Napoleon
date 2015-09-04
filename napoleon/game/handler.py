import logging

import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
from tornado.websocket import WebSocketHandler
import tornado.escape
from collections import defaultdict
from napoleon import card
from . import state
from . import phase


logger = logging.getLogger(__name__)


class WSHandlerMixin(object):
    connections = defaultdict(set)

    @property
    def room_id(self):
        return self.path_kwargs["room_id"]

    def check_origin(self, origin):
        return True

    def open(self, room_id):
        WSHandlerMixin.connections[room_id].add(self)

    def on_close(self):
        WSHandlerMixin.connections[self.room_id].remove(self)

    def to_json(self, message):
        return tornado.escape.json_decode(message)

    def write_on_same_room(self, json):
        message = tornado.escape.json_encode(json)
        for con in WSHandlerMixin.connections[self.room_id]:
            try:
                con.write_message(message)
            except tornado.websocket.WebSocketClosedError:
                pass


class GameHandler(WSHandlerMixin, WebSocketHandler):
    """
    Returns a game state which any player can get.
    Every time a player change a state, including a private state,
    all the player have to update the public state.
    Also there are some audience, and then they have to update it.
    """

    def on_message(self, message):
        # TODO: validate message
        try:
            json = self.to_json(message)
        except ValueError:
            return

        action = json.pop("action", "")
        sid = json.pop("session_id")
        s = state.GameState(self.room_id)
        myself = state.Myself(session_id=sid, state=s)

        p = phase.get_action(s.phase, action)
        if p is None:
            return

        if not s.phase:
            p(**json).act(myself)
        elif s.phase == "declare" and action == "declare":
            p(**json).act(myself)
        elif s.phase == "declare" and action == "pass":
            p(**json).act(myself)
        elif s.phase == "adjutant":
            p(**json).act(myself)
        elif s.phase == "discard":
            p(**json).act(myself)
        elif s.phase in ["first_round", "rounds"]:
            if s._phase.waiting_next_turn:
                s._phase.next_round()
            myself.select(card.from_int(int(json["selected"])))
        s.next()
        # p.next()

        self.write_on_same_room({"update": True})
