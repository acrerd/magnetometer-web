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
        # last received time
        last_time = streams[0].get_last_time()

        # earliest time to retrieve data for
        raw_start_time = last_time - datetime.timedelta(hours = 1)
        trend_start_time = last_time - datetime.timedelta(hours = 6)

        # raw data streams
        raw_streams = [stream.get_time_series(since=raw_start_time) \
        for stream in streams if stream.stream_type == "raw"]

        # trend data streams
        trend_streams = [stream.get_time_series(since=trend_start_time) \
        for stream in streams if stream.stream_type == "trend"]

        # convert data to JavaScript
        raw_streams_js = [utils.stream_to_js(data) for data in raw_streams]
        trend_streams_js = [utils.stream_to_js(data) for data in trend_streams]

        return render.index(raw_streams_js=raw_streams_js, \
        trend_streams_js=trend_streams_js, \
        raw_data_since=utils.format_date_time(raw_start_time, config), \
        trend_data_since=utils.format_date_time(trend_start_time, config))

if __name__ == "__main__":
    web.httpserver.runsimple(app.wsgifunc(), ("0.0.0.0", 50000))
