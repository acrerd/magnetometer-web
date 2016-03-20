from __future__ import division

import datetime

def format_date_time(dateobj, config):
    """Formats the specified date

    :param dateobj: datetime object
    :param config: config file
    """

    return dateobj.strftime("{0} {1}".format(\
    config.get('general', 'date_format'), config.get('general', 'time_format')))

def stream_to_js(stream):
    js_str = ""

    if len(stream) > 0:
        # convert entries to JavaScript format
        js_str += ",".join(["[{0}, {1}]".format(str(sample[0]), str(sample[1])) \
        for sample in stream])

    return "[" + js_str + "]"
