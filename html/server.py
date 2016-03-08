import web

import models
from picolog.data import DataStore

urls = (
    "/insert", "Insert",
    "/?", "List"
)

app = web.application(urls, globals())

class BaseController:
    def __init__(self):
        self.db = web.database(dbn='sqlite', db='test.db')

class List(BaseController):
    def GET(self):
        data_model = models.MagnetometerDataModel(self.db)

        data = data_model.get_samples("hello")

        return data

class Insert(BaseController):
    """Methods to insert data"""

    def POST(self):
        # get POST data, but also get GET data
        data = web.input(_method="both")

        # create datastore from POST data
        datastore = DataStore.instance_from_json(data['data'])

        # get key from GET data
        key = data['key']

        # data model
        data_model = models.MagnetometerDataModel(self.db)

        # insert data
        try:
            insert_count = data_model.add_data(datastore, key)

            return "{0} samples added".format(insert_count)
        except Exception:
            return "No access with specified key"

if __name__ == "__main__":
    app.run()
