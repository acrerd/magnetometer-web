from __future__ import division

import web.db
import datetime
import itertools

from picolog.data import Sample
from picolog.constants import Channel
import utils

"""Data models"""

class DatabaseModel:
    """Represents a database model"""

    """The database connection"""
    _db = None

    """The configuration file"""
    config = None

    def __init__(self, db, config):
        """Initialises the magnetometer data model

        :param db: database object
        """

        # set database
        self._db = db

        # set config
        self.config = config

class AccessKeyModel(DatabaseModel):
    """Represents the access keys model"""

    def init_schema(self):
        """Initialises the database schema"""

        # create table
        with self._db.transaction():
            self._db.query('''
                CREATE TABLE access_keys (
	               key_id INTEGER PRIMARY KEY,
                   key TEXT NOT NULL
                )
            ''')

    def add_key(self, key):
        """Adds a new key"""

        # start a transaction
        with self._db.transaction():
            # insert key
            return self._db.insert('access_keys', key=key)

class ChannelAccessModel(DatabaseModel):
    """Represents the channel access model"""

    # access modes, in ascending order of access
    MODE_NONE = 0 # no access
    MODE_R = 1 # read-only
    MODE_RW = 2 # read and write

    def init_schema(self):
        """Initialises the database schema"""

        # create table
        with self._db.transaction():
            self._db.query('''
                CREATE TABLE channel_access (
	               channel INTEGER UNSIGNED NOT NULL,
                   key_id INTEGER NOT NULL,
                   mode TINYINT UNSIGNED NOT NULL,
                   FOREIGN KEY(channel) REFERENCES channels(channel),
                   FOREIGN KEY(key_id) REFERENCES access_keys(key_id)
                )
            ''')

    def add_channel_access(self, channel, key_id, mode):
        """Allows channel access to the specified key"""

        # start a transaction
        with self._db.transaction():
            # insert access
            return self._db.insert('channel_access', channel=channel, \
            key_id=key_id, mode=mode)

    def get_writable_channels(self, key):
        """Returns a list of writable channels for the specified key"""

        result = self._db.query('''
            SELECT channel
            FROM channel_access
            INNER JOIN access_keys
            ON channel_access.key_id = access_keys.key_id
            WHERE access_keys.key = $key AND mode = $mode
        ''', {'key': key, 'mode': self.MODE_RW})

        return [allowed_channel.channel for allowed_channel in result.list()]

    def get_readable_channels(self, key):
        """Returns a list of writable channels for the specified key"""

        result = self._db.query('''
            SELECT channel
            FROM channel_access
            INNER JOIN access_keys
            ON channel_access.key_id = access_keys.key_id
            WHERE access_keys.key = $key AND mode >= $mode
        ''', {'key': key, 'mode': self.MODE_R})

        return [allowed_channel.channel for allowed_channel in result.list()]

class MagnetometerChannelModel(DatabaseModel):
    """Represents the magnetometer channel structure"""

    def init_schema(self):
        """Initialises the database schema"""

        # create table
        with self._db.transaction():
            self._db.query('''
                CREATE TABLE channels (
	               channel INTEGER UNSIGNED NOT NULL,
                   name TEXT NOT NULL,
                   CONSTRAINT channel_index UNIQUE (channel)
                )
            ''')

    def add_channel(self, channel, name):
        """Adds a channel to the database

        :param channel: the channel number to add
        :param name: the name to add
        :raises Exception: if channel is invalid
        """

        # check that channel is valid
        if not Channel.is_valid(channel):
            raise Exception("Specified channel is not valid")

        # start a transaction
        with self._db.transaction():
            # insert channel
            self._db.insert('channels', channel=channel, name=name)

    def get_channel_name(self, channel):
        """Returns channel name"""

        return self._db.select('channels', {"channel": channel}, \
        where="channel = $channel")

class MagnetometerDataModel(DatabaseModel):
    """Represents the magnetometer data structure"""

    def init_schema(self):
        """Initialises the database schema"""

        # create table
        self._db.query('''
            CREATE TABLE samples (
	            channel INTEGER UNSIGNED NOT NULL,
                timestamp DATETIME(3) NOT NULL,
	            value INTEGER NOT NULL,
                FOREIGN KEY(channel) REFERENCES channels(channel),
                CONSTRAINT sample_index UNIQUE (channel, timestamp)
                ON CONFLICT IGNORE
            )
        ''')

    def add_data(self, datastore, key):
        """Adds readings from a datastore to the database

        :param datastore: the datastore object to add readings from
        """

        # get allowed channels
        allowed_channels = ChannelAccessModel(self._db, \
        self.config).get_writable_channels(key)

        insert_count = 0

        # start a transaction
        with self._db.transaction():
            # insert samples, checking channel access
            for sample in itertools.chain.from_iterable(datastore.sample_dict_gen()):
                if sample['channel'] not in allowed_channels:
                    raise Exception("Channel {0} cannot be writen to with \
specified key".format(sample['channel']))

                self._db.insert('samples', channel=sample['channel'], \
                timestamp=sample['timestamp'], value=sample['value'])

                insert_count += 1

        return insert_count

    def get_channel_time_series(self, key, channel, *args, **kwargs):
        """Returns time series for the specified channel"""

        # get allowed channels
        allowed_channels = ChannelAccessModel(self._db, \
        self.config).get_readable_channels(key)

        # check access
        if channel not in allowed_channels:
            # return empty list
            return []

        # get rows
        rows = self._db.select('samples', {'channel': int(channel)}, \
        where='channel = $channel', *args, **kwargs)

        # create timeseries from rows
        return [[row.timestamp, row.value] for row in rows \
        if row.channel in allowed_channels]

    def get_multi_channel_time_series(self, key, channels, since=None, *args, \
    **kwargs):
        """Returns time series for multiple channels as specified"""

        # get allowed channels
        allowed_channels = ChannelAccessModel(self._db, \
        self.config).get_readable_channels(key)

        # empty where clause
        where = []

        # specify allowed channels
        where.append(web.db.sqlors('channel = ', [i for i in channels \
        if i in allowed_channels]))

        # create since command (and convert timestamp from s to ms)
        if since is not None:
            where.append("timestamp >= {0}".format(int(since.strftime("%s")) * 1000))

        # create full where command
        sqlwhere = " AND ".join([str(clause) for clause in where])

        # get rows
        rows = self._db.select('samples', where=sqlwhere, order="channel ASC", \
        *args, **kwargs)

        # create multiple time series from rows
        # for some reason, list(v) doesn't work, so we need [i for i in v]
        return [[[i.timestamp, i.value] for i in v] for k, v in itertools.groupby(rows, \
        lambda x: x.channel)]

    def get_last_received_time(self):
        """Gets the time of the last data received"""

        # get timestamp, in ms
        timestamp = self._db.select_single_cell('samples', what="timestamp", \
        order="timestamp DESC")

        # check if it is valid
        if timestamp is not None:
            # convert to s
            timestamp = int(timestamp) / 1000
        else:
            timestamp = 0

        # return date object
        return datetime.datetime.utcfromtimestamp(timestamp)
