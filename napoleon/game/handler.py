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

        action = json.get("action")
        s = state.GameState(self.room_id)
        myself = state.Myself(session_id=json["session_id"], state=s)

        if not s.phase:
            s.start()
        elif s.phase == "declare" and action == "declare":
            declaration = card.from_int(int(json["declaration"]))
            myself.declare(declaration)
        elif s.phase == "declare" and action == "pass":
            myself.pass_()
        elif s.phase == "adjutant":
            myself.decide(card.from_int(int(json["adjutant"])))
            s.set_role(card.from_int(int(json["adjutant"])))
        elif s.phase == "discard":
            myself.discard(card.from_list(json["unused"]))
            myself.select(card.from_int(int(json["selected"])))
        elif s.phase in ["first_round", "rounds"]:
            if s._phase.waiting_next_turn:
                s._phase.next_round()
            myself.select(card.from_int(int(json["selected"])))
        s.next()

        self.write_on_same_room({"update": True})
