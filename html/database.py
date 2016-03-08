import web

class MagnetometerDatabase(object):
    """Magnetometer database class"""

    @classmethod
    def instance(cls):
        # get database
        db = web.database(dbn='sqlite', db='test.db') # FIXME: use config file

        # turn on foreign key support
        db.query("PRAGMA foreign_keys=ON")

        return db
