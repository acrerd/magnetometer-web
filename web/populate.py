import sys
import web
import models

from config import get_config
from database import Database
from picolog.data import DataStore, Reading, Sample

###
# get config

# path to config file, if specified
config_path = None

if len(sys.argv) > 1:
    config_path = sys.argv[1]

config = get_config(config_path)

###
# populate database

db = Database(config)
key = "UuF0ZUOyCIEJ4RmqMepvOv"

keys = models.AccessKeyModel(db, config)
keys.init_schema()
key_id = keys.add_key(key)

channels = models.MagnetometerChannelModel(db, config)
channels.init_schema()

channels.add_channel(13, "Channel 13")
channels.add_channel(14, "Channel 14")
channels.add_channel(15, "Channel 15")
channels.add_channel(16, "Channel 16")

channel_access = models.ChannelAccessModel(db, config)
channel_access.init_schema()
channel_access.add_channel_access(13, key_id, models.ChannelAccessModel.MODE_RW)
channel_access.add_channel_access(14, key_id, models.ChannelAccessModel.MODE_RW)
channel_access.add_channel_access(15, key_id, models.ChannelAccessModel.MODE_RW)
channel_access.add_channel_access(16, key_id, models.ChannelAccessModel.MODE_RW)

magnetometer = models.MagnetometerDataModel(db, config)
magnetometer.init_schema()

# example of adding data
#datastore = DataStore(100)
#datastore.insert([Reading(0, [1,2,3], [10, 20, 30]), Reading(1, [1,2,3], [11, 21, 31])])
#magnetometer.add_data(datastore, key)
