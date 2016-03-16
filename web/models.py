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

    @staticmethod
    def datetime_to_timestamp(dateobj):
        """Returns a timestamp for use in database queries

        Assumes ms units, which should be used everywhere in the data models.
        """

        return int(dateobj.strftime("%s")) * 1000

    @staticmethod
    def timestamp_to_datetime(timestamp):
        """Returns a datetime object using a database timestamp

        Assumes ms units for the timestamp
        """

        # check if it is valid
        if timestamp is not None:
            # convert to s
            timestamp = int(timestamp) / 1000
        else:
            timestamp = 0

        # return date object
        return datetime.datetime.utcfromtimestamp(timestamp)

class AccessKeyModel(DatabaseModel):
    """Represents the access keys model"""

    def init_schema(self):
        """Initialises the database schema"""

        # create table
        with self._db.transaction():
            self._db.query("""
                CREATE TABLE access_keys (
	               key_id INTEGER PRIMARY KEY,
                   key TEXT NOT NULL
                )
            """)

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
            self._db.query("""
                CREATE TABLE channel_access (
	               channel INTEGER UNSIGNED NOT NULL,
                   key_id INTEGER NOT NULL,
                   mode TINYINT UNSIGNED NOT NULL,
                   FOREIGN KEY(channel) REFERENCES channels(channel),
                   FOREIGN KEY(key_id) REFERENCES access_keys(key_id)
                )
            """)

    def add_channel_access(self, channel, key_id, mode):
        """Allows channel access to the specified key"""

        # start a transaction
        with self._db.transaction():
            # insert access
            return self._db.insert('channel_access', channel=channel, \
            key_id=key_id, mode=mode)

    def get_writable_channels(self, key):
        """Returns a list of writable channels for the specified key"""

        result = self._db.query("""
            SELECT channel
            FROM channel_access
            INNER JOIN access_keys
            ON channel_access.key_id = access_keys.key_id
            WHERE access_keys.key = $key AND mode = $mode
        """, {'key': key, 'mode': self.MODE_RW})

        return [allowed_channel.channel for allowed_channel in result.list()]

    def get_readable_channels(self, key):
        """Returns a list of writable channels for the specified key"""

        result = self._db.query("""
            SELECT channel
            FROM channel_access
            INNER JOIN access_keys
            ON channel_access.key_id = access_keys.key_id
            WHERE access_keys.key = $key AND mode >= $mode
        """, {'key': key, 'mode': self.MODE_R})

        return [allowed_channel.channel for allowed_channel in result.list()]

class MagnetometerChannelModel(DatabaseModel):
    """Represents the magnetometer channel structure"""

    def init_schema(self):
        """Initialises the database schema"""

        # create table
        with self._db.transaction():
            self._db.query("""
                CREATE TABLE channels (
	               channel INTEGER UNSIGNED NOT NULL,
                   name TEXT NOT NULL,
                   CONSTRAINT channel_index UNIQUE (channel)
                )
            """)

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

    def get_channel_time_series(self, key, channel, since=None, \
    *args, **kwargs):
        """Returns time series for the specified channel"""

        # get allowed channels
        allowed_channels = ChannelAccessModel(self._db, \
        self.config).get_readable_channels(key)

        # check access
        if channel not in allowed_channels:
            # return empty list
            return []

        # empty where clause
        where = []

        # add channel
        where.append("channel = {0}".format(int(channel)))

        # create since command (and convert timestamp from s to ms)
        if since is not None:
            # threshold timestamp, in ms
            since_timestamp = self.datetime_to_timestamp(since)

            where.append("timestamp >= {0}".format(since_timestamp))

        # create full where command
        sqlwhere = " AND ".join([str(clause) for clause in where])

        # get rows
        rows = self._db.select(MagnetometerDataModel.SAMPLE_TABLE_NAME, \
        where=sqlwhere, order="timestamp ASC", *args, **kwargs)

        # create timeseries from rows
        return [[row.timestamp, row.value] for row in rows \
        if row.channel in allowed_channels]

class MagnetometerDataModel(DatabaseModel):
    """Represents the magnetometer data structure"""

    """Table name"""
    SAMPLE_TABLE_NAME = "samples"

    def init_schema(self):
        """Initialises the database schema"""

        # create table
        self._db.query("""
            CREATE TABLE {0} (
	            channel INTEGER UNSIGNED NOT NULL,
                timestamp DATETIME(3) NOT NULL,
	            value INTEGER NOT NULL,
                FOREIGN KEY(channel) REFERENCES channels(channel),
                CONSTRAINT sample_index UNIQUE (channel, timestamp)
                ON CONFLICT IGNORE
            )
        """.format(self.SAMPLE_TABLE_NAME))

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

                self._db.insert(self.SAMPLE_TABLE_NAME, \
                channel=sample['channel'], timestamp=sample['timestamp'], \
                value=sample['value'])

                insert_count += 1

        return insert_count

    def get_last_received_time(self):
        """Gets the time of the last data received"""

        # get timestamp, in ms
        timestamp = self._db.select_single_cell(self.SAMPLE_TABLE_NAME, \
        what="timestamp", order="timestamp DESC")

        # return date object
        return self.timestamp_to_datetime(timestamp)

class MagnetometerDataTrendModel(DatabaseModel):
    """Represents a data trend for a magnetometer data structure"""

    """Channel"""
    channel = None

    """Time average [ms]"""
    timestamp_avg = None

    def __init__(self, channel, timestamp_avg, *args, **kwargs):
        # initialise parent
        DatabaseModel.__init__(self, *args, **kwargs)

        # set channel
        self.channel = channel

        # set time average
        self.timestamp_avg = timestamp_avg

    def init_schema(self):
        """Initialises the database schema"""

        # create table
        self._db.query("""
            CREATE TABLE {0} (
	            channel INTEGER UNSIGNED NOT NULL,
                timestamp DATETIME(3) NOT NULL,
	            value INTEGER NOT NULL,
                FOREIGN KEY(channel) REFERENCES channels(channel),
                CONSTRAINT sample_index UNIQUE (channel, timestamp)
                ON CONFLICT IGNORE
            )
        """.format(self._table_name()))

    def _table_name(self):
        """Returns the table name"""

        return "{0}_trend_{1}_{2}".format(\
        str(MagnetometerDataModel.SAMPLE_TABLE_NAME), int(self.channel), \
        int(self.timestamp_avg))

    def compute_trends(self, max_rows=1000):
        """Computes trends following the last computed trend value"""

        # get last computed trend
        last_trend_time = self.get_last_computed_trend_time()

        # create where clause
        where = []

        # add timestamp threshold
        where.append("timestamp >= {0}".format( \
        self.datetime_to_timestamp(last_trend_time)))

        # add channel
        where.append("channel == {0}".format(int(self.channel)))

        # create SQL where clause
        sqlwhere = " AND ".join(where)

        # fetch unaveraged rows
        rows = self._db.select(MagnetometerDataModel.SAMPLE_TABLE_NAME, \
        where=sqlwhere, order="timestamp ASC", limit=int(max_rows)).list()

        # check that spanned time is at least enough to make an average
        if rows[-1].timestamp - rows[0].timestamp < self.timestamp_avg:
            raise Exception("The maximum number of rows is not enough to span \
the specified trend time.")

        # timestamp of previous row (by default, first row)
        last_timestamp = rows[0].timestamp

        # indices
        index = 1
        window_start_index = 0

        # time since start of trend window
        window_accumulated_time = 0

        # trend times and values
        trend_times = []
        trend_values = []

        for row in rows:
            window_accumulated_time += row.timestamp - last_timestamp

            # have we reached the trend time?
            if window_accumulated_time >= self.timestamp_avg:
                # compute trend with this window
                trend_values.append(self._compute_trend(rows[window_start_index:index]))

                # add time
                trend_times.append(row.timestamp)

                # reset the window start index, equal to the next row
                window_start_index = index

                # reset window accumulated time
                window_accumulated_time = 0

            # update last timestamp
            last_timestamp = row.timestamp

            # increment index
            index += 1

        return trend_times, trend_values

    def _compute_trend(self, rows):
        """Computes the trend value for the specified rows"""

        return sum([row.value for row in rows]) / len(rows)

    def get_last_computed_trend_time(self):
        """Fetches the time of the last computed trend"""

        # get timestamp, in ms
        timestamp = self._db.select_single_cell(self._table_name(), \
        what="timestamp", order="timestamp DESC")

        # return date object
        return self.timestamp_to_datetime(timestamp)
