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
key = "UuF0ZUOyCIEJ4RmqMepvOv"

trends = models.MagnetometerDataTrendModel(13, 10000, db, config)
#trends.init_schema()
print trends.compute_trends()
