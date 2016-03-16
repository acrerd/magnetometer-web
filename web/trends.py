import sys
import web
import models

from config import get_config
from database import Database

###
# get config

# path to config file, if specified
config_path = None

if len(sys.argv) > 1:
    config_path = sys.argv[1]

config = get_config(config_path)

db = Database(config)
key = models.Key("UuF0ZUOyCIEJ4RmqMepvOv", db, config)

channel_2 = models.Channel(13, db, config)
channel_2_trends = models.ChannelSampleTrends(channel_2, key, 10000, db, config)
#channel_2_trends.init_schema()

inserted_row_count = channel_2_trends.update_trends(max_rows=1000)
print "{0} rows inserted".format(inserted_row_count)
