import web
import models

from picolog.data import DataStore, Reading, Sample

db = web.database(dbn='sqlite', db='test.db')

magnetometer = models.MagnetometerDataModel(db)
magnetometer.init_schema()

datastore = DataStore(100)
datastore.insert([Reading(0, [1,2,3], [10, 20, 30]), Reading(1, [1,2,3], [11, 21, 31])])

magnetometer.add_data(datastore)
