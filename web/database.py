import web.db

class Database(web.db.SqliteDB):
    """Magnetometer database class"""

    def __init__(self, config):
        # call parent - the old style way because web.db doesn't use new style
        # classes
        web.db.SqliteDB.__init__(self, db=config.get('database', 'path'))

        # turn on foreign key support
        self.query("PRAGMA foreign_keys=ON")

    def select_single_row(self, *args, **kwargs):
        """Selects and returns a single row"""

        # make sure limit == 1
        if 'limit' in kwargs:
            if kwargs['limit'] is not 1:
                raise Exception("Limit must be 1")
        else:
            kwargs['limit'] = 1

        select = self.select(*args, **kwargs).list()

        if len(select) > 0:
            # return the first row of the query result
            return select[0]
        else:
            return None

    def select_single_cell(self, *args, **kwargs):
        """Selects and returns one value"""

        # make sure there's only one what
        if 'what' in kwargs:
            if len(kwargs['what'].split(',')) is not 1:
                raise Exception("Only one column can be specified")
        else:
            raise Exception("Column not specified")

        # get row
        row = self.select_single_row(*args, **kwargs)

        if row is not None:
            # return column
            return row[kwargs['what']]
        else:
            return None
