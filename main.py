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

If you want to log to stderr, run this with an option::

    python main.py --log_to_stderr

"""


if __name__ == "__main__":
    wsgi_app = WSGIContainer(application)
    app = Application(make_rootings(fallback_handler=wsgi_app), debug=settings.DEBUG)
    server = HTTPServer(app)

    # after loading wsgi_app
    parse()

    # use PORT env variable on heroku
    port = int(os.environ.get("PORT", options.port))
    server.listen(port)

    logger.info("Start main.py server at port = %s" % port)
    tornado.ioloop.IOLoop.instance().start()
