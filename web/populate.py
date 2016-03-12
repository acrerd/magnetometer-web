import web
import models

from database import MagnetometerDatabase
from picolog.data import DataStore, Reading, Sample

db = MagnetometerDatabase.instance()
key = "hello"

keys = models.AccessKeyModel(db)
keys.init_schema()
key_id = keys.add_key(key)

channels = models.MagnetometerChannelModel(db)
channels.init_schema()

channels.add_channel(1, "Channel 1")
channels.add_channel(2, "Channel 2")
channels.add_channel(3, "Channel 3")
channels.add_channel(4, "Channel 4")

channel_access = models.ChannelAccessModel(db)
channel_access.init_schema()
channel_access.add_channel_access(1, key_id, models.ChannelAccessModel.MODE_RW)
channel_access.add_channel_access(2, key_id, models.ChannelAccessModel.MODE_RW)
channel_access.add_channel_access(3, key_id, models.ChannelAccessModel.MODE_RW)
channel_access.add_channel_access(4, key_id, models.ChannelAccessModel.MODE_RW)

magnetometer = models.MagnetometerDataModel(db)
magnetometer.init_schema()

datastore = DataStore(100)
datastore.insert([Reading(0, [1,2,3], [10, 20, 30]), Reading(1, [1,2,3], [11, 21, 31])])

magnetometer.add_data(datastore, key)
