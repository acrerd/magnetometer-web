import sys
import os
import web
import datetime

from config import init_settings_from_argv
import utils
import models
import database
import api
from picolog.data import DataStore

config, db, server_key, channels, streams = init_settings_from_argv()

###
# Start web application

# URL routing
urls = (
    "/api", api.app_api,
    "/?", "List"
)

# create application object
app = web.application(urls, globals())

# create template renderer
render = web.template.render("templates", base='base')

class BaseController:
    pass

class List(BaseController):
    def GET(self):
        # raw data streams
        raw_streams = [stream for stream in streams if stream.stream_type == "raw"]

        # trend data streams
        trend_streams = [stream for stream in streams if stream.stream_type == "trend"]

        stream_sets = [{"description": "Measurements", "streams": raw_streams}, \
        {"description": "Trends", "streams": trend_streams}]

        return render.index(stream_sets=stream_sets)

if __name__ == "__main__":
    web.httpserver.runsimple(app.wsgifunc(), ("0.0.0.0", 50000))
