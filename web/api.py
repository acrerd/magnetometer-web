import sys
import web
import time

from config import get_config
import models
import database
from picolog.data import Reading

# URL routing
urls = (
    "/(.+)/data/(.+)", "DataManager"
)

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
            last_data_time = \
            models.ChannelSamples(channel_1, server_key, db, config).get_last_time()

            # return UNIX timestamp, in ms
            return time.mktime(last_data_time.timetuple()) * 1000
        else:
            return web.notfound()

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
