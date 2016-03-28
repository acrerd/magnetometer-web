import sys
import web
import time

from config import init_settings_from_argv
import models
import database
from picolog.data import Reading

config, db, server_key, channels, streams = init_settings_from_argv()

# URL routing
urls = (
    "/(.+)/data/(.+)", "DataManager"
)

app_api = web.application(urls, globals())

class BaseController(object):
    pass

class DataManager(BaseController):
    """Methods to manage data"""

    def GET(self, key, command):
        # handle "latest"
        if command == "latest/timestamp":
            # get last time
            # FIXME: make a Reading class to access last full reading time
            # HACK: use a single channel's last time
            last_data_time = last_time = streams[0].get_last_time()

            # set status
            web.ctx.status = '200 OK'

            # return UNIX timestamp, in ms
            return str(time.mktime(last_data_time.utctimetuple()) * 1000)
        else:
            return web.notfound()

    def PUT(self, key, timestamp):
        # get data
        data = web.data()

        # create reading from data
        reading = Reading.instance_from_json(data)

        # get key from GET data
        client_key = models.Key(key, db, config)

        # insert data
        try:
            insert_count = models.ChannelSamples.add_from_reading(db, \
            client_key, reading)
        except Exception, e:
            print e
            return e

        # set return status to signify creation
        web.ctx.status = '201 Created'

        # return number of samples added
        return "{0} samples added".format(insert_count)
