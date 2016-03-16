import sys
import os
import web
import datetime

from config import get_config
import utils
import models
import database
from picolog.data import DataStore

# URL routing
urls = (
    "/insert", "Insert",
    "/?", "List"
)

###
# get config

# path to config file, if specified
config_path = None

if len(sys.argv) > 1:
    config_path = sys.argv[1]

config = get_config(config_path)

###
# Start web application

# create application object
app = web.application(urls, globals())

# create template renderer
render = web.template.render("templates", base='base')

class BaseController:
    def __init__(self):
        self.db = database.Database(config)

class List(BaseController):
    def GET(self):
        data_model = models.MagnetometerDataModel(self.db, config)
        channel_model = models.MagnetometerChannelModel(self.db, config)

        # last received time
        last_received_time = data_model.get_last_received_time()

        # earliest time to retrieve data for
        start_time = last_received_time - datetime.timedelta(hours = 1)

        key = "UuF0ZUOyCIEJ4RmqMepvOv"
        data = []
        data.append(channel_model.get_channel_time_series(key, 16, \
        since=start_time))
        data.append(channel_model.get_channel_time_series(key, 13, \
        since=start_time))
        data.append(channel_model.get_channel_time_series(key, 14, \
        since=start_time))

        if len(data) > 0:
            # convert entries to JavaScript format
            data_js = [",".join(["[{0}, {1}]".format(str(entry[0]), str(entry[1])) \
            for entry in series]) for series in data]
        else:
            data_js = [[], [], []]

        return render.index(data_js=data_js, \
        data_since=utils.format_date_time(start_time, config))

class Insert(BaseController):
    """Methods to insert data"""

    def POST(self):
        # get POST data, but also get GET data
        data = web.input(_method="both")

        # create datastore from POST data
        datastore = DataStore.instance_from_json(data['data'])

        # get key from GET data
        key = data['key']

        # data model
        data_model = models.MagnetometerDataModel(self.db, config)

        # insert data
        try:
            insert_count = data_model.add_data(datastore, key)

            return "{0} samples added".format(insert_count)
        except Exception, e:
            #return "No access with specified key"
            return e

if __name__ == "__main__":
    web.httpserver.runsimple(app.wsgifunc(), ("0.0.0.0", 50000))
