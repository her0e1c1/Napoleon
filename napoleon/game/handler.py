import logging

from tornado import gen
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
from tornado.websocket import WebSocketHandler
import tornado.escape
from collections import defaultdict
from . state import GameState
from . session import Session
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
        self.state = GameState(self.adaptor)

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

    def _take_action(self, json, player):
        action_name = json.pop("action", "")
        action_class = phase.get_action(self.state.phase.current, action_name)

        if not action_class:
            return False

        action = action_class(player)
        if action.can_next:
            action.act(**json)
            action.next()
            return True

        return False

    @gen.coroutine
    def on_message(self, message):
        # TODO: validate message
        try:
            json = self.to_json(message)
        except ValueError:
            yield
            raise gen.Return()

        sid = json.pop("session_id")
        session = Session(self.adaptor, session_id=sid)
        self._take_action(json, self.state.create_player(session.user_id))
        yield self.write_on_same_room({"update": True})
        yield self.handle_ai()

    @gen.coroutine
    def handle_ai(self):
        """
        If all the player AI have no action to the current state, then exit it.
        Otherwise a player AI changes the state, so it needs to check whether
        all the player AI have a action to the changed state. If at least one
        of them have it, they act recusively.
        """

        for player in self.state.player_AIs:
            json = player._AI.get_action()
            if json:
                logger.info("AI action: %s => %s" % (player, json))

                # AI must wait for human's acitons here
                yield gen.sleep(1)

                if self._take_action(json, player):
                    yield self.write_on_same_room({"update": True})
                    yield self.handle_ai()
                    break
