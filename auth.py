from flask_peewee.auth import Auth

from shoptet_api.app import app, db
from shoptet_api.models import SysUser


authentification = Auth(app, db, user_model=SysUser)
