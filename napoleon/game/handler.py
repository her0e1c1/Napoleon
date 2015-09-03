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

        mode = json.get("mode")
        pgs = state.PrivateGameState(session_id=json["session_id"], room_id=self.room_id)
        s = state.GameState(self.room_id)
        if not pgs.phase:
            s.start()
            pgs.phase = "declare"
        elif mode == "declare":
            pgs.declaration = json["declaration"]
            if pgs.is_napoleon_determined:
                pgs.phase = "adjutant"
        elif mode == "pass":
            pgs.set_pass_ids()
            if pgs.is_napoleon_determined:
                pgs.phase = "adjutant"
            elif pgs.are_all_players_passed:
                pgs.phase = None
        elif mode == "adjutant":
            pgs.adjutant = json["adjutant"]
            pgs.set_role(int(json["adjutant"]))
            pgs.phase = "discard"
        elif pgs.phase == "discard":
            pgs.discard(json["unused"])
            pgs.select(int(json["selected"]))
            pgs.next()
            pgs.phase = "first_round"
        elif pgs.phase == "first_round":
            if pgs.waiting_next_turn:
                pgs.next_round()
                pgs.phase = "rounds"
            pgs.select(json["selected"])
            pgs.next()
        elif pgs.phase == "rounds":
            if pgs.waiting_next_turn:
                pgs.next_round()
            pgs.select(json["selected"])
            pgs.next()
            if pgs.is_finished:
                # record
                pgs.phase = "finished"

        self.write_on_same_room({"update": True})
