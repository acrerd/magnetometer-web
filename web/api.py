import web
import time

import models
from picolog.data import Reading

# URL routing
urls = (
    "/(.+)/data/", "DataManager"
)

# create application object
app_api = web.application(urls, globals())

class BaseController:
    pass

class DataManager(BaseController):
    """Methods to manage data"""

    def GET(self, key):
        # get data
        data = web.input(_method="both")

        # handle "latest"
        if data["path"] == "latest":
            # get last time
            # FIXME: make a Reading class to access last full reading time
            # HACK: use a single channel's last time
            last_data_time = ChannelSamples(channel_1, server_key).get_last_time()

            # return UNIX timestamp
            return time.mktime(last_data_time.time_tuple())

    def PUT(self, key):
        # get data
        data = web.input(_method="both")

        # create reading from data
        reading = Reading.instance_from_json(data)

        # get key from GET data
        client_key = models.Key(key, db, config)

        # insert data
        try:
            insert_count = models.ChannelSamples.add_from_reading(db, key, \
            reading)

            return "{0} samples added".format(insert_count)
        except Exception, e:
            #return "No access with specified key"
            raise
            #return e
