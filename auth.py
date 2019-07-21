from flask_peewee.auth import Auth

from app import app, db
from models import SysUser


authentification = Auth(app, db, user_model=SysUser)
