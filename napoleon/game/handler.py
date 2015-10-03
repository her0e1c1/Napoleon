import logging

from tornado import gen
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
from tornado.websocket import WebSocketHandler
import tornado.escape
from collections import defaultdict
from . import state
from . import phase
from . adaptor import RedisAdaptor


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
        self.adaptor = RedisAdaptor(room_id)

    def on_close(self):
        WSHandlerMixin.connections[self.room_id].remove(self)
        # self.adaptor.conn.close()  # ???

    def to_json(self, message):
        return tornado.escape.json_decode(message)

    @gen.coroutine
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

    @gen.coroutine
    def on_message(self, message):
        # TODO: validate message
        try:
            json = self.to_json(message)
        except ValueError:
            yield
            raise gen.Return()

        action_name = json.pop("action", "")
        sid = json.pop("session_id")

        try:
            myself = state.Myself(session_id=sid, state=state.GameState(self.adaptor))
        except state.InvalidSession:
            yield self.write_on_same_room({"update": True})
            raise gen.Return()

        action_class = phase.get_action(myself.state.phase.current, action_name)
        if not action_class:
            yield self.write_on_same_room({"update": True})
            raise gen.Return()

        action = action_class(myself)
        if action.can_next:
            action.act(**json)
            action.next()

        yield self.write_on_same_room({"update": True})

        yield self.handle_ai(myself.state)

    @gen.coroutine
    def handle_ai(self, state):
        """
        If all the player AI have no action to the current state, then exit it.
        Otherwise a player AI changes the state, so it needs to check whether
        all the player AI have a action to the changed state. If at least one
        of them have it, they act recusively.
        """

        for player in state.player_AIs:
            json = player._AI.get_action()
            if json:
                logger.info("AI action: %s => %s" % (player, json))

                # AI must wait for human's acitons here
                yield gen.sleep(1)

                action_class = phase.get_action(state.phase.current, json.pop("action"))
                if action_class:
                    action = action_class(player)
                    action.act(**json)
                    action.next()
                    yield self.write_on_same_room({"update": True})
                    yield self.handle_ai(player.state)
