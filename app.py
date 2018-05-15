from flask import Flask

# flask-peewee bindings
from flask_peewee.db import Database
from peewee import SqliteDatabase


app = Flask(__name__)
app.config.from_object('config.Configuration')

# db = Database(app)
db = SqliteDatabase('shoptet.db')

# from shoptet_api.models import SysUser, User, Order, OrderLine, Log, Voucher, Shop
#
# def create_tables():
#     SysUser.create_table()
#     User.create_table()
#     Order.create_table()
#     OrderLine.create_table()
#     Log.create_table()
#     Voucher.create_table()
#     Shop.create_table()
