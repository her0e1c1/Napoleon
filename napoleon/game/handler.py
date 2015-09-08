import logging

import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
from tornado.websocket import WebSocketHandler
import tornado.escape
from collections import defaultdict
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

        action_name = json.pop("action", "")
        sid = json.pop("session_id")

        try:
            myself = state.Myself(session_id=sid, state=state.GameState(self.room_id))
        except state.InvalidSession:
            return self.write_on_same_room({"update": True})

        action_class = phase.get_action(myself.state.phase, action_name)
        if not action_class:
            return self.write_on_same_room({"update": True})

        action = action_class(myself)
        if action.can_next:
            action.act(**json)
            action.next()
        self.write_on_same_room({"update": True})
