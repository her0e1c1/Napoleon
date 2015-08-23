import tornado.ioloop
import tornado.web
import tornado.websocket
from tornado.websocket import WebSocketHandler
import tornado.escape
from collections import defaultdict
import card
import state


class WSHandlerMixin(object):
    connections = defaultdict(set)

    @property
    def room_id(self):
        return self.path_kwargs["game_id"]

    def check_origin(self, origin):
        return True

    def open(self, game_id):
        room_id = game_id
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
        if mode == "join":
            state.set_user_id(self.room_id, json["session_id"], json["user_id"])
            pgs = state.PrivateGameState(session_id=json["session_id"], room_id=self.room_id)
            pgs.join()
        elif mode == "quit":
            pgs = state.PrivateGameState(session_id=json["session_id"], room_id=self.room_id)
            pgs.quit()
        elif mode == "start":
            # TODO: I must make the initial action only one time
            pgs = state.PrivateGameState(room_id=self.room_id)
            players = pgs.players
            number_of_players = len(players)
            if number_of_players <= 2:  # TODO: catch an error
                return
            hands, rest = card.deal(number_of_players)
            pgs.rest = rest
            for (p, h) in zip(players, hands):
                st = state.PrivateGameState(user_id=p, room_id=self.room_id)
                st.hand = h
        elif mode == "declare":
            pgs = state.PrivateGameState(room_id=self.room_id, session_id=json["session_id"])
            pgs.declaration = json["declaration"]
        elif mode == "pass":
            pgs = state.PrivateGameState(room_id=self.room_id, session_id=json["session_id"])
            pgs.set_pass_ids()
        elif mode == "unused":
            pass

        self.write_on_same_room({"update": True})


def make_app():
    return tornado.web.Application([
        (r"/game/(?P<game_id>\d+)", GameHandler),
    ])


if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()
