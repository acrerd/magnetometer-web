from __future__ import division

import datetime

def format_date_time(dateobj, config):
    """Formats the specified timestamp

    :param dateobj: datetime object
    :param config: config file
    """

    return dateobj.strftime("{0} {1}".format(\
    config.get('general', 'date_format'), config.get('general', 'time_format')))
