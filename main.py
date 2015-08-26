import os

import tornado
from tornado.options import options, define, parse_command_line
from tornado.httpserver import HTTPServer
from tornado.wsgi import WSGIContainer
from tornado.web import Application
from tornado.web import FallbackHandler

from napoleon.handlers.game import GameHandler


if __name__ == "__main__":
    define("port", type=int, default=80)
    parse_command_line()
    from napoleon.wsgi import application
    wsgi_app = WSGIContainer(application)
    app = Application([
        (r"/room/(?P<room_id>\d+)", GameHandler),
        (r".*", FallbackHandler, {"fallback": wsgi_app}),
    ])
    server = HTTPServer(app)
    port = int(os.environ.get("PORT", options.port))
    server.listen(port)
    tornado.ioloop.IOLoop.instance().start()
