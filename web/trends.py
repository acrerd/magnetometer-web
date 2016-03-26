import sys
import web
import models

from config import init_settings_from_argv
from database import Database

config, db, server_key, channels, streams = init_settings_from_argv()

def update_trends(max_rows=2500):
    # update trends
    for trend in [trend for trend in streams if trend.stream_type == "trend"]:
        inserted_row_count = trend.update_trends(max_rows=max_rows)

        print "{0} rows inserted for trend {1}".format(inserted_row_count, trend)

def add_trend(channel_num, window, timestamp_avg):
    # channel
    channel = models.Channel(channel_num, "Default", db, config)

    # trend
    trend = models.ChannelSampleTrends(channel, "trend", window, server_key, \
    timestamp_avg, db=db, config=config)

    # initialise trend
    trend.init_schema()

def delete_trend(channel_num, window, timestamp_avg):
    # channel
    channel = models.Channel(channel_num, "Default", db, config)

    # trend
    trend = models.ChannelSampleTrends(channel, "trend", window, server_key, \
    timestamp_avg, db=db, config=config)

    # delete
    trend.delete()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "add":
            add_trend(*sys.argv[2:])

            print "Trend added"
        elif sys.argv[1] == "delete":
            delete_trend(*sys.argv[2:])

            print "Trend deleted"
        else:
            print "Unrecognised command"
    else:
        # no argument provided
        update_trends()
