import os
import logging

from django.conf import settings

import tornado
from tornado.options import options
from tornado.httpserver import HTTPServer
from tornado.wsgi import WSGIContainer
from tornado.web import Application

from napoleon.wsgi import application
from main_tornado import make_rootings, parse

logger = logging.getLogger(__name__)


"""
How to serve
============

On heroku production, you can serve only one web server.
To serve tornado and django at one time, run this ::

    python main.py

"""


if __name__ == "__main__":
    wsgi_app = WSGIContainer(application)
    app = Application(make_rootings(fallback_handler=wsgi_app), debug=settings.DEBUG)
    server = HTTPServer(app)

    parse()  # after loading wsgi_app
    # use PORT env variable on heroku
    port = int(os.environ.get("PORT", options.port))
    server.listen(port)

    logger.info("Start main.py server at port = %s" % options.port)

    tornado.ioloop.IOLoop.instance().start()
