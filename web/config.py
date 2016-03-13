import os
import ConfigParser
import web

def parse_config(config_path):
    # create the config object
    parser = ConfigParser.RawConfigParser()

    # first of all, parse the default configuration
    parser.read("config" + os.path.sep + "config.default")

    # next, parse the user-defined configuration if present
    if config_path:
        parser.read(config_path)

    return parser

def set_web_settings(config):
    # debug mode
    web.config.debug = bool(config.get('general', 'debug'))

def get_config(config_path):
    config = parse_config(config_path)

    set_web_settings(config)

    return config
