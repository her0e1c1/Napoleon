import os

import tornado
from tornado.options import options, define, parse_command_line
from tornado.httpserver import HTTPServer
from tornado.wsgi import WSGIContainer
from tornado.websocket import WebSocketHandler
from tornado.web import Application
from tornado.web import FallbackHandler

import django
import django.core.handlers.wsgi

from napoleon.handlers.game import GameHandler

define("port", type=int, default=80)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "napoleon.settings")
django.setup()


class HelloHandler(WebSocketHandler):
    def on_message(self, room_id):
        self.write_message('Hello from tornado')

settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "napoleon/static"),
}

if __name__ == "__main__":
    parse_command_line()
    wsgi_app = WSGIContainer(django.core.handlers.wsgi.WSGIHandler())
    app = Application([
        # (r"/room/(?P<room_id>\d+)", GameHandler),
        # (r".*", FallbackHandler, {"fallback": wsgi_app}),
    ], **settings)
    server = HTTPServer(app)
    port = int(os.environ.get("PORT", options.port))
    server.listen(port)
    # tornado.ioloop.IOLoop.current().start()
    tornado.ioloop.IOLoop.instance().start()
