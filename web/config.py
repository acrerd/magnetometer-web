import sys
import os
import ConfigParser
import web

from collections import OrderedDict

from models import Channel, ChannelSamples, ChannelSampleTrends, Key
from database import Database

def parse_config(config_path, default_path):
    # create the config object
    parser = ConfigParser.RawConfigParser()

    if default_path is not None:
        # parse the default configuration
        parser.read(default_path)

    # parse the user-defined configuration if present
    if config_path:
        parser.read(config_path)

    return parser

def get_config(config_path, default_path=None):
    config = parse_config(config_path, default_path)

    return config

def init_settings(config, channel_config, stream_config):
    # set debug mode etc.
    set_web_settings(config)

    # create database
    db = Database(config.get('database', 'path'))

    # create key
    key = Key(config.get('general', 'key'), db, config)

    # get channels
    channels = parse_channels(channel_config, db=db, config=config)

    # channel samples
    streams = parse_streams(stream_config, channels=channels, key=key, db=db, \
    config=config)

    # return site info
    return (config, db, key, channels, streams)

def init_settings_from_argv():
    # path to config files, if specified
    config_path = None
    channel_config_path = None
    stream_config_path = None

    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    if len(sys.argv) > 2:
        channel_config_path = sys.argv[2]
    if len(sys.argv) > 3:
        stream_config_path = sys.argv[3]

    config = get_config(config_path, "config" + os.path.sep + "config.default")
    channel_config = get_config(channel_config_path, \
    "config" + os.path.sep + "channel_config.default")
    stream_config = get_config(stream_config_path, \
    "config" + os.path.sep + "stream_config.default")

    return init_settings(config, channel_config, stream_config)

def parse_channels(channel_config, *args, **kwargs):
    """Returns channels based on the specified info"""

    # parse and return channels
    return [Channel(int(channel_config.get(section, "channel")), \
    channel_config.get(section, "name"), *args, **kwargs) \
    for section in channel_config.sections()]

def parse_streams(stream_config, *args, **kwargs):
    return [parse_stream(stream_config, section, *args, **kwargs) \
    for section in stream_config.sections()]

def parse_stream(stream_config, section, channels, key, db, config):
    # get stream type
    stream_type = stream_config.get(section, "type")

    # get channel
    stream_channel = None

    # window
    window = stream_config.get(section, "window")

    for channel in channels:
        if int(stream_config.get(section, "channel")) is channel.channel_num:
            stream_channel = channel

            break

    if stream_channel is None:
        raise Exception("Specified stream channel is not configured")

    if stream_type == "raw":
        return ChannelSamples(channel, stream_type=stream_type, window=window, \
        key=key, db=db, config=config)
    elif stream_type == "trend":
        return ChannelSampleTrends(stream_channel, stream_type=stream_type, \
        window=window, key=key, timestamp_avg=int(stream_config.get(section, \
        "integration_time")), db=db, config=config)
    else:
        raise TypeError("Unrecognised stream type")

def set_web_settings(config):
    # debug mode
    web.config.debug = bool(config.get('general', 'debug'))
