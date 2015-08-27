import tornado
from napoleon.game.handler import GameHandler


def make_app():
    return tornado.web.Application([
        (r"/ws/(?P<room_id>\d+)", GameHandler),
    ])


if __name__ == "__main__":
    tornado.options.parse_command_line()
    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()
