import datetime
import string

from peewee import *

db = SqliteDatabase('shoptet.db')


# TODO make mapping from shoptet to choices (regex?)
# there will be multiple options merged to one
ORDER_STATUS_CHOICES = [
    ('new', 'Prijatá'),
    ('prepared', 'Pripravená'),
    ('completed', 'Vybavená'),
    ('cancelled', 'Stornovaná')

]

LOG_ENTITIES = [
    ('user', 'User'),
    ('order', 'Order'),
    ('voucher', 'Voucher'),
    ('system', 'System'),
]

LOG_EVENTS = [
    ('create', 'Create'),
    ('read', 'Read'),
    ('update', 'Update'),
    ('delete', 'Delete'),
]

ROLES = [
    ('sysuser', 'System User'),
    ('admin', 'Admin'),
    ('wizard', 'Wizard'),
]


class DBModel(Model):
    class Meta:
        database = db

    create_date = DateTimeField()
    # write_date = DateTimeField()

    def save(self):
        _now = datetime.datetime.now()
        if not self.id:
            self.__data__.update({'create_date': _now})
        # self.__data__.update({'write_date': _now})
        return super().save()


class SysUser(DBModel):
    username = CharField()
    password = CharField()
    role = CharField(choices=ROLES, default='sysuser')


class MissingKeyError(BaseException):
    pass


check_code_or_email = Check('code is not null or email is not null')


class User(DBModel):
    code = CharField(null=True, constraints=[check_code_or_email])
    email = CharField(null=True, constraints=[check_code_or_email])
    name = CharField(null=True)
    street = CharField(null=True)
    zip = CharField(null=True)
    city = CharField(null=True)
    country = CharField(null=True)
    phone = CharField(null=True)


class Order(DBModel):
    order_shop_id = IntegerField()
    order_num = CharField()
    amount = DecimalField()
    amount_applicable = DecimalField(null=True)
    discount = DecimalField(null=True)
    shipping = CharField(null=True)
    shipping_cost = DecimalField(null=True)
    status = CharField(choices=ORDER_STATUS_CHOICES)
    user_id = ForeignKeyField(User, backref='orders')
    open_date = DateField()
    close_date = DateField()


class OrderLine(DBModel):
    order_id = ForeignKeyField(Order, backref='order_lines')
    code = CharField()
    description = CharField()
    amount = DecimalField()
    unit = CharField(null=True)
    unit_price = DecimalField()
    vat_rate = DecimalField()
    total_price = DecimalField()


class Voucher(DBModel):
    voucher_id = IntegerField()
    voucher_code = CharField()
    voucher_type = CharField(null=True)
    amount = DecimalField(null=True)
    valid_from = DateField(null=True)
    valid_to = DateField(null=True)
    user_id = ForeignKeyField(User, backref='orders')


class Log(DBModel):
    log_time = DateTimeField()
    event = CharField(choices=LOG_EVENTS)
    user_id = ForeignKeyField(SysUser, backref='logs', null=True)
    details = CharField(null=True)


# DATABASE HANDLING
def save_order(order_details):
    uinfo = order_details.get('user_info')
    key = next(i for i in ['email', 'code'] if uinfo)
    value = uinfo.get(key, None)
    user = None
    try:
        user = User.get(**{key: value})
    except User.DoesNotExist:
        pass

    # if user does not exist, we create a new one
    if not user:
        user = User(**uinfo)
        user.save()

    order = None
    try:
        order = Order.get(order_shop_id=order_details.get('order_shop_id'))
    except:
        order = None
    if not order:
        fields = [d for d in dir(User._schema.model)
                  if not d.startswith('_') and not d.startswith(string.uppercase)]
        order_keys = {key: value for key, value in order_details.items()
                      if key in fields}
        order_shop_id = IntegerField()
        order_num = CharField()
        amount = DecimalField()
        amount_applicable = DecimalField(null=True)
        discount = DecimalField(null=True)
        shipping = CharField(null=True)
        shipping_cost = DecimalField(null=True)
        status = CharField(choices=ORDER_STATUS_CHOICES)
        user_id = ForeignKeyField(User, backref='orders')
        open_date = DateField()
        close_date = DateField()

        order = Order(**keys)
        order.save()
    for order_line in order_details.get('order_lines', []):
        order_id = order.id
        OrderLine()

    if uinfo:
        # find if user exists in database
        if 'email' in uinfo:
            User.get(email=uinfo['email'])
        elif 'code' in uinfo:
            User.get(code=uinfo['code'])

        for key in ['email', 'code']:
            if key in uinfo:
                User.get(**{key: uinfo[key]})
                break
        else:
            raise MissingKeyError


def init_db():
    with db:
        db.create_tables([SysUser, User, Order, OrderLine, Voucher, Log])


if __name__ == '__main__':
    init_db()
    pass