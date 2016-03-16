from __future__ import division

import web.db
import datetime
import itertools

from picolog.data import Sample
from picolog.constants import Channel
import utils

"""Data models"""

class DatabaseModel(object):
    """Represents a database model"""

    """The database connection"""
    db = None

    """The configuration file"""
    config = None

    def __init__(self, db, config):
        """Initialises the magnetometer data model

        :param db: database object
        """

        # set database
        self.db = db

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

class Channel(DatabaseModel):
    """Represents a channel"""

    """Channel"""
    channel_num = None

    def __init__(self, channel_num, *args, **kwargs):
        """Initialises a database channel model"""

        super(Channel, self).__init__(*args, **kwargs)

        # set channel
        self.channel_num = int(channel_num)

    @classmethod
    def init_schema(cls, db):
        """Initialises the database schema"""

        # create table
        with db.transaction():
            db.query("""
                CREATE TABLE channels (
	               channel INTEGER UNSIGNED NOT NULL,
                   name TEXT NOT NULL,
                   CONSTRAINT channel_index UNIQUE (channel)
                )
            """)

    def add(self, name):
        """Adds a channel to the database

        :param name: the name to add
        :raises Exception: if channel is invalid
        """

        # check that channel is valid
        if not Channel.is_valid(self.channel_num):
            raise Exception("Specified channel is not valid")

        # start a transaction
        with self.db.transaction():
            # insert channel
            self.db.insert('channels', channel=self.channel_num, name=name)

    def get_name(self):
        """Returns channel name"""

        return str(self.db.select_single_row('channels', \
        {"channel": self.channel_num}, what="name", where="channel = $channel"))

class Key(DatabaseModel):
    """Represents a key"""

    """Key value"""
    key_value = None

    def __init__(self, key_value, *args, **kwargs):
        super(Key, self).__init__(*args, **kwargs)

        self.key_value = key_value

    @classmethod
    def init_schema(cls, db):
        """Initialises the database schema"""

        # create table
        with db.transaction():
            db.query("""
                CREATE TABLE access_keys (
	               key_id INTEGER PRIMARY KEY,
                   key TEXT NOT NULL
                )
            """)

    def add(self):
        """Adds a new key"""

        # start a transaction
        with self.db.transaction():
            # insert key
            return self.db.insert('access_keys', key=self.key_value)

    def get_id(self):
        """Returns the key id for the predefined key"""

        return int(self.db.select_single_cell('access_keys', \
        {"key": self.key_value}, what="key_id", where="key = $key"))

    def get_writable_channels(self):
        """Returns a list of writable channels for the specified key"""

        result = self.db.query("""
            SELECT channel
            FROM channel_access
            INNER JOIN access_keys
            ON channel_access.key_id = access_keys.key_id
            WHERE access_keys.key = $key AND mode = $mode
        """, {'key': self.key_value, 'mode': ChannelAccess.MODE_RW})

        return [allowed_channel.channel for allowed_channel in result.list()]

    def get_readable_channels(self):
        """Returns a list of writable channels for the specified key"""

        result = self.db.query("""
            SELECT channel
            FROM channel_access
            INNER JOIN access_keys
            ON channel_access.key_id = access_keys.key_id
            WHERE access_keys.key = $key AND mode >= $mode
        """, {'key': self.key_value, 'mode': ChannelAccess.MODE_R})

        return [allowed_channel.channel for allowed_channel in result.list()]

class ChannelAccess(DatabaseModel):
    """Represents the channel access model"""

    # access modes, in ascending order of access
    MODE_NONE = 0 # no access
    MODE_R = 1 # read-only
    MODE_RW = 2 # read and write

    """Channel"""
    channel = None

    """Key"""
    key = None

    def __init__(self, channel, key, *args, **kwargs):
        super(ChannelAccess, self).__init__(*args, **kwargs)

        self.channel = channel
        self.key = key

    @classmethod
    def init_schema(cls, db):
        """Initialises the database schema"""

        # create table
        with db.transaction():
            db.query("""
                CREATE TABLE channel_access (
	               channel INTEGER UNSIGNED NOT NULL,
                   key_id INTEGER NOT NULL,
                   mode TINYINT UNSIGNED NOT NULL,
                   FOREIGN KEY(channel) REFERENCES channels(channel),
                   FOREIGN KEY(key_id) REFERENCES access_keys(key_id)
                )
            """)

    def add(self, mode):
        """Allows channel access to the specified key"""

        # start a transaction
        with self.db.transaction():
            # insert access
            return self.db.insert('channel_access', \
            channel=self.channel.get_id(), key_id=self.key.get_id(), mode=mode)

class ChannelSamples(DatabaseModel):
    """Represents the magnetometer data"""

    """Channel"""
    channel = None

    """Key"""
    key = None

    """Table name"""
    TABLE_NAME = "samples"

    def __init__(self, channel, key, *args, **kwargs):
        super(ChannelSamples, self).__init__(*args, **kwargs)

        self.channel = channel
        self.key = key

    @classmethod
    def init_schema(cls, db):
        """Initialises the database schema"""

        # create table
        db.query("""
            CREATE TABLE {0} (
	            channel INTEGER UNSIGNED NOT NULL,
                timestamp DATETIME(3) NOT NULL,
	            value INTEGER NOT NULL,
                FOREIGN KEY(channel) REFERENCES channels(channel),
                CONSTRAINT sample_index UNIQUE (channel, timestamp)
                ON CONFLICT IGNORE
            )
        """.format(cls.TABLE_NAME))

    @classmethod
    def add_from_datastore(cls, db, key, datastore):
        """Adds readings from a datastore to the database

        :param datastore: the datastore object to add readings from
        """

        # get allowed channels
        allowed_channels = key.get_writable_channels()

        insert_count = 0

        # start a transaction
        with db.transaction():
            # insert samples, checking channel access
            for sample in itertools.chain.from_iterable(datastore.sample_dict_gen()):
                if sample['channel'] not in allowed_channels:
                    raise Exception("Channel {0} cannot be writen to with \
specified key".format(sample['channel']))

                db.insert(cls.TABLE_NAME, \
                channel=sample['channel'], timestamp=sample['timestamp'], \
                value=sample['value'])

                insert_count += 1

        return insert_count

    def get_time_series(self, since=None, *args, **kwargs):
        """Returns time series for this channel"""

        # get allowed channels
        allowed_channels = self.key.get_writable_channels()

        # check access
        if self.channel.channel_num not in allowed_channels:
            # return empty list
            return []

        # empty where clause
        where = []

        # add channel
        where.append("channel = {0}".format(self.channel.channel_num))

        # create since command (and convert timestamp from s to ms)
        if since is not None:
            # threshold timestamp, in ms
            since_timestamp = self.datetime_to_timestamp(since)

            where.append("timestamp >= {0}".format(since_timestamp))

        # create full where command
        sqlwhere = " AND ".join([str(clause) for clause in where])

        # get rows
        rows = self.db.select(self.TABLE_NAME, \
        where=sqlwhere, order="timestamp ASC", *args, **kwargs)

        # create timeseries from rows
        return [[row.timestamp, row.value] for row in rows \
        if row.channel in allowed_channels]

    def get_last_time(self):
        """Gets the time of the last data in the table"""

        # get timestamp, in ms
        timestamp = self.db.select_single_cell(self.TABLE_NAME, \
        what="timestamp", order="timestamp DESC")

        # return date object
        return self.timestamp_to_datetime(timestamp)

class ChannelSampleTrends(DatabaseModel):
    """Represents a data trend for a magnetometer data structure"""

    """Channel"""
    channel = None

    """Key"""
    key = None

    """Time average [ms]"""
    timestamp_avg = None

    def __init__(self, channel, key, timestamp_avg, *args, **kwargs):
        # initialise parent
        super(ChannelSampleTrends, self).__init__(*args, **kwargs)

        # set channel
        self.channel = channel

        # set key
        self.key = key

        # set time average
        self.timestamp_avg = int(timestamp_avg)

    def init_schema(self):
        """Initialises the database schema"""

        # create table
        self.db.query("""
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
        str(ChannelSamples.TABLE_NAME), self.channel.channel_num, self.timestamp_avg)

    def _add_trend_data(self, times, values):
        """Adds the trend data specified as times and values to the table"""

        # create data: list of dicts representing rows
        data = []

        for time, value in zip(times, values):
            data.append({"channel": self.channel.channel_num, "timestamp": time, \
            "value": value})

        # add data
        with self.db.transaction():
            row_ids = self.db.multiple_insert(self._table_name(), data)

        # return number of rows inserted
        return len(row_ids)

    def update_trends(self, max_rows=1000):
        """Updates the trends based on new data since latest computed trend"""

        # calculate trends
        try:
            trend_times, trend_values = self._calculate_trends(max_rows)
        except NoDataForTrendsException:
            # no data available, so return 0 as the number of new trend points
            return 0

        # insert into database, returning the number of new trend points
        return self._add_trend_data(trend_times, trend_values)

    def _calculate_trends(self, max_rows):
        """Computes trends following the last computed trend value"""

        # get last computed trend
        last_trend_time = self.get_last_trend_time()

        # create where clause
        where = []

        # add timestamp threshold
        where.append("timestamp >= {0}".format( \
        self.datetime_to_timestamp(last_trend_time)))

        # add channel
        where.append("channel == {0}".format(self.channel.channel_num))

        # create SQL where clause
        sqlwhere = " AND ".join(where)

        # fetch unaveraged rows
        rows = self.db.select(ChannelSamples.TABLE_NAME, where=sqlwhere, \
        order="timestamp ASC", limit=int(max_rows)).list()

        # check that spanned time is at least enough to make an average
        if rows[-1].timestamp - rows[0].timestamp < self.timestamp_avg:
            raise NoDataForTrendsException("The maximum number of rows is not \
enough to span the specified trend time.")

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

    def get_last_trend_time(self):
        """Fetches the time of the last computed trend"""

        # get timestamp, in ms
        timestamp = self.db.select_single_cell(self._table_name(), \
        what="timestamp", order="timestamp DESC")

        # return date object
        return self.timestamp_to_datetime(timestamp)

    def get_time_series(self, since=None, *args, **kwargs):
        """Returns time series for this channel trend"""

        # allowed channels
        allowed_channels = self.key.get_writable_channels()

        # check access
        if self.channel.channel_num not in allowed_channels:
            # return empty list
            return []

        # empty where clause
        where = []

        # add channel
        where.append("channel = {0}".format(self.channel.channel_num))

        # create since command (and convert timestamp from s to ms)
        if since is not None:
            # threshold timestamp, in ms
            since_timestamp = self.datetime_to_timestamp(since)

            where.append("timestamp >= {0}".format(since_timestamp))

        # create full where command
        sqlwhere = " AND ".join([str(clause) for clause in where])

        # get rows
        rows = self.db.select(self._table_name(), \
        where=sqlwhere, order="timestamp ASC", *args, **kwargs)

        # create timeseries from rows
        return [[row.timestamp, row.value] for row in rows \
        if row.channel in allowed_channels]

class NoDataForTrendsException(Exception):
    pass
