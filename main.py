from shoptet_api.app import app, db

from shoptet_api.auth import *
from shoptet_api.admin import admin
from shoptet_api.api import api
from shoptet_api.models import *
from shoptet_api.views import *

admin.setup()
api.setup()


if __name__ == '__main__':
    app.run()
