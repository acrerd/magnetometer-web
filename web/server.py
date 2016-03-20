import sys
import os
import web
import datetime

from config import get_config
import utils
import models
import database
import api
from picolog.data import DataStore

###
# get config

# path to config file, if specified
config_path = None

if len(sys.argv) > 1:
    config_path = sys.argv[1]

config = get_config(config_path)

db = database.Database(config)
server_key = models.Key("UuF0ZUOyCIEJ4RmqMepvOv", db, config)

channel_1 = models.Channel(16, db, config)
channel_2 = models.Channel(13, db, config)
channel_3 = models.Channel(14, db, config)

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
        # channel data
        channel_data_1 = models.ChannelSamples(channel_1, server_key, db, config)
        channel_data_2 = models.ChannelSamples(channel_2, server_key, db, config)
        channel_data_3 = models.ChannelSamples(channel_3, server_key, db, config)

        # trend data, 10s average, last 6 hours
        channel_data_2_trend = models.ChannelSampleTrends(channel_2, server_key, \
        10000, db, config)

        # last received time
        last_raw_time = channel_data_1.get_last_time()
        last_trend_time = channel_data_2_trend.get_last_trend_time()

        # earliest time to retrieve data for
        raw_start_time = last_raw_time - datetime.timedelta(hours = 1)
        trend_start_time = last_trend_time - datetime.timedelta(hours = 6)

        data = []
        data.append(channel_data_1.get_time_series(since=raw_start_time))
        data.append(channel_data_2.get_time_series(since=raw_start_time))
        data.append(channel_data_3.get_time_series(since=raw_start_time))
        data.append(channel_data_2_trend.get_time_series(since=trend_start_time))

        if len(data) > 0:
            # convert entries to JavaScript format
            data_js = [",".join(["[{0}, {1}]".format(str(entry[0]), str(entry[1])) \
            for entry in series]) for series in data]
        else:
            data_js = [[], [], [], []]

        return render.index(data_js=data_js, \
        raw_data_since=utils.format_date_time(raw_start_time, config), \
        trend_data_since=utils.format_date_time(trend_start_time, config))

if __name__ == "__main__":
    web.httpserver.runsimple(app.wsgifunc(), ("0.0.0.0", 50001))
