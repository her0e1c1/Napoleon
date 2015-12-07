import logging

from django.conf import settings

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
    def path(self):
        return self.request.path

    def check_origin(self, origin):
        return True

    def open(self, room_id):
        sid = self.get_cookie("sessionid")
        WSHandlerMixin.connections[self.path].add((self, sid,))
        if sid.startswith("anonymous_"):
            self.adaptor = RedisAdaptor(room_id, timer=settings.GAME_TIME_FOR_ANONYMOUS_PLAYER)
        else:
            self.adaptor = RedisAdaptor(room_id)
        self.state = GameState(self.adaptor)

    def on_close(self):
        sid = self.get_cookie("sessionid")
        WSHandlerMixin.connections[self.path].remove((self, sid,))

    def to_json(self, message):
        return tornado.escape.json_decode(message)

    @gen.coroutine
    def write_on_same_room(self, message):
        message = tornado.escape.json_encode(message)
        for con, sid in WSHandlerMixin.connections[self.path]:
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

    def _take_action(self, json, user_id):
        action_name = json.pop("action", "")
        action_class = phase.get_action(self.state.phase.current, action_name)

        if not action_class:
            return False

        # player must be without session
        player = self.state.create_player(user_id)
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
        if session.user_id:
            self._take_action(json, session.user_id)
            yield self.write_on_same_room()
            yield self.handle_ai()
        else:
            yield self.write_on_same_room()

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

                if self._take_action(json, player.user_id):
                    yield self.write_on_same_room()
                    yield self.handle_ai()
                    break

    @gen.coroutine
    def write_on_same_room(self):
        for con, sid in WSHandlerMixin.connections[self.path]:
            session = Session(self.adaptor, session_id=sid)
            message = tornado.escape.json_encode(session.state.to_json())
            try:
                con.write_message(message)
            except tornado.websocket.WebSocketClosedError:
                pass
