import sys
import web
import models

from config import init_settings_from_argv
from database import Database

config, db, server_key, channels, streams = init_settings_from_argv()

for trend in [trend for trend in streams if trend.stream_type == "trend"]:
    inserted_row_count = trend.update_trends(max_rows=1000)

    print "{0} rows inserted for trend {1}".format(inserted_row_count, trend)
