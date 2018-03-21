from peewee import *

db = SqliteDatabase('shoptet.db')


class DBModel(Model):
    class Meta:
        database = db


class User(DBModel):
    email = CharField()
    name = CharField()
    street = CharField()
    zip = CharField()
    city = CharField()
    country = CharField()
    phone = CharField()


class Order(DBModel):
    order_id = IntegerField()
    order_num = CharField()
    amount = DecimalField()
    amount_applicable = DecimalField()
    discount = DecimalField()
    shipping = CharField()
    shipping_cost = DecimalField()
    status = CharField()
    user_id = ForeignKeyField(User, backref='orders')


class Voucher(DBModel):
    voucher_id = IntegerField()
    voucher_code = CharField()
    voucher_type = CharField()
    amount = DecimalField()
    valid_from = DateField()
    valid_to = DateField()
    user_id = ForeignKeyField(User, backref='orders')


def init_db():
    with db:
        db.create_tables([User, Order, Voucher])