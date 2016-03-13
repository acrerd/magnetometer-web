from __future__ import division

import datetime

def format_date_time(timestamp, date_format, time_format):
    """Formats the specified timestamp

    :param timestamp: UNIX timestamp, in ms
    :param date_format: date format
    :param time_format: time format
    """

    return datetime.datetime.fromtimestamp(timestamp / 1000).strftime(\
    "{0} {1}".format(date_format, time_format))
