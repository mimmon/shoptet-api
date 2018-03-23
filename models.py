from peewee import *

db = SqliteDatabase('shoptet.db')


class DBModel(Model):
    class Meta:
        database = db


class User(DBModel):
    code = CharField()
    email = CharField(null=True)
    name = CharField(null=True)
    street = CharField(null=True)
    zip = CharField(null=True)
    city = CharField(null=True)
    country = CharField(null=True)
    phone = CharField(null=True)


# TODO make mapping from shoptet to choices (regex?)
# there will be multiple options merged to one
ORDER_STATUS_CHOICES = [
    ('new', 'Prijatá'),
    ('prepared', 'Pripravená'),
    ('completed', 'Vybavená'),
    ('cancelled', 'Stornovaná')

]


class Order(DBModel):
    order_id = IntegerField()
    order_num = CharField()
    amount = DecimalField()
    amount_applicable = DecimalField(null=True)
    discount = DecimalField(null=True)
    shipping = CharField(null=True)
    shipping_cost = DecimalField(null=True)
    status = CharField(choices=ORDER_STATUS_CHOICES)
    user_id = ForeignKeyField(User, backref='orders')


class Voucher(DBModel):
    voucher_id = IntegerField()
    voucher_code = CharField()
    voucher_type = CharField(null=True)
    amount = DecimalField(null=True)
    valid_from = DateField(null=True)
    valid_to = DateField(null=True)
    user_id = ForeignKeyField(User, backref='orders')


def init_db():
    with db:
        db.create_tables([User, Order, Voucher])


if __name__ == '__main__':
    # init_db()
    pass