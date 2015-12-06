import os
import logging

from django import setup
from django.conf import settings

import tornado
from tornado.options import options, define, parse_command_line
from tornado.web import Application, FallbackHandler
from tornado.log import enable_pretty_logging

from napoleon.game.handler import GameHandler
from napoleon.chat.handler import ChatHandler

logger = logging.getLogger(__name__)


"""
How to serve
============
tornado depends on only a django setting file.
::

    python main_tornado.py
    python manage.py runserver 0.0.0.0:8000 --noreload --settings=napoleon.settings.local

"""


def parse():
    define("port",
           type=int,
           default=settings.TORNADO_PORT,
           help="a number to bind port for tornado")
    parse_command_line()


def make_rootings(fallback_handler=None):
    """
    :fallback_handler: wsgi_app if not matching routings
    """
    rootings = [
        (r"/ws/(?P<room_id>\w+)", GameHandler),
        (r"/chat/(?P<room_id>\w+)", ChatHandler),
    ]
    if fallback_handler:
        rootings.append((r".*", FallbackHandler, {"fallback": fallback_handler}))

    return rootings

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "napoleon.settings.local")
    setup()

    parse()
    app = Application(make_rootings(), debug=settings.DEBUG)
    app.listen(options.port)

    enable_pretty_logging()
    logger.info("Start main_tornado.py server at port = %s" % options.port)

    tornado.ioloop.IOLoop.current().start()
