import datetime
import itertools

"""Data models"""

class MagnetometerDataModel:
    """Represents the magnetometer data structure"""

    """The database connection"""
    _db = None

    def __init__(self, db):
        """Initialises the magnetometer data model

        :param db: database object
        """

        # set database
        self._db = db

    def init_schema(self):
        """Initialises the database schema"""

        # create table
        self._db.query('''
            CREATE TABLE samples (
	           `channel` INTEGER UNSIGNED NOT NULL,
               `timestamp` DATETIME(3) NOT NULL,
	            `value` INTEGER NOT NULL,
                CONSTRAINT `sample_index` UNIQUE (`channel`, `timestamp`)
                    ON CONFLICT IGNORE)
        ''')

    def add_data(self, datastore):
        """Adds readings from a datastore to the database

        :param datastore: the datastore object to add readings from
        """

        # start a transaction
        with self._db.transaction():
            # insert samples
            self._db.multiple_insert('samples', \
            values=itertools.chain.from_iterable(datastore.sample_dict_gen()))

    def get_data(self):
        """Returns data"""

        data = self._db.select('samples')

        return data
