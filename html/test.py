import web

import models

urls = ("/.*", "Index")
app = web.application(urls, globals())

class BaseController:
    pass

class Index(BaseController):
    def GET(self):
        db = web.database(dbn='sqlite', db='test.db')

        model = models.MagnetometerDataModel(db)

        data = model.get_data()

        return ", ".join([str(row.channel) for row in data])

if __name__ == "__main__":
    app.run()
