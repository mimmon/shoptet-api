import datetime
from decimal import Decimal
import random
import re
import string

from peewee import *

db = SqliteDatabase('shoptet.db')


# TODO make mapping from shoptet to choices (regex?)
# there will be multiple options merged to one
# ORDER_STATUS_CHOICES = [
#     ('new', 'Prijatá'),
#     ('prepared', 'Pripravená'),
#     ('completed', 'Vybavená'),
#     ('cancelled', 'Stornovaná')
# ]

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

    create_date = DateTimeField(default=datetime.datetime.now)
    write_date = DateTimeField(default=datetime.datetime.now)

    def save(self, *args, **kwargs):
        _now = datetime.datetime.now()
        self.__data__.update({'write_date': _now})
        return super().save(*args, **kwargs)


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


class Shop(DBModel):
    name = CharField()
    email = CharField(null=True)
    image = CharField(null=True)
    web = CharField(null=True)
    street = CharField(null=True)
    zip = CharField(null=True)
    city = CharField(null=True)
    country = CharField(null=True)
    phone = CharField(null=True)


class Order(DBModel):
    shop_order_id = IntegerField(null=True)
    order_num = CharField(null=True)
    price_no_vat = DecimalField()
    vat = DecimalField()
    total_price = DecimalField()
    price_applicable = DecimalField(null=True)  # price applicable for loyalty system
    discount = DecimalField(null=True)          # if any, no loyalty
    shipping = CharField(null=True)
    shipping_cost = DecimalField(null=True)     # this does not count in loyalty system
    status = CharField(default='')   #choices=ORDER_STATUS_CHOICES)
    user_id = ForeignKeyField(User, backref='orders')
    open_date = DateTimeField()
    close_date = DateTimeField(null=True)
    url = CharField(null=True)       # used for storing url in eshop for easier access
    next_url = CharField(null=True)  # url of the next order
    closed = BooleanField(default=False)


class OrderLine(DBModel):
    order_id = ForeignKeyField(Order, backref='order_lines')
    code = CharField(null=True)
    description = CharField(default='')
    amount = DecimalField()
    unit = CharField(null=True)
    unit_price = DecimalField()
    vat_rate = DecimalField()
    total_price = DecimalField()
    discount_percent = DecimalField(null=True)
    image = CharField(null=True)


class Voucher(DBModel):
    voucher_id = IntegerField()
    voucher_code = CharField()
    voucher_type = CharField(null=True)
    amount = DecimalField(null=True)
    valid_from = DateField(null=True)
    valid_to = DateField(null=True)
    user_id = ForeignKeyField(User, backref='orders')


class Log(DBModel):
    log_time = DateTimeField(default=datetime.datetime.now)
    event = CharField(choices=LOG_EVENTS)
    model = CharField(null=True)
    record = IntegerField(null=True)
    user_id = ForeignKeyField(SysUser, backref='logs', null=True)
    details = CharField(null=True)


def process_order_line(order_line):
    code = order_line.get('code', None)
    description = order_line.get('description', '')
    amount = Decimal(order_line.get('amount', '0'))
    unit = None
    unit_price = Decimal(order_line.get('unit_price', '0.00'))
    vat_rate = Decimal(order_line.get('vat_rate', '20.0'))
    total_price = Decimal(order_line.get('total_vat_including', '0.0'))
    image = order_line.get('img')
    discount_percent = order_line.get('discount_percent')
    return {
        'code': code, 'description': description, 'amount': amount, 'unit': unit,
        'unit_price': unit_price, 'vat_rate': vat_rate, 'total_price': total_price,
        'image': image, 'discount_percent': discount_percent
    }


# DATABASE HANDLING
def save_order(order_details, update=True):
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
        char_pool = string.ascii_lowercase+string.ascii_uppercase+string.digits
        if not uinfo.get('email') and not uinfo.get('code'):
            while True:
                random_uid = '__' + ''.join(random.choice(char_pool) for _ in range(16))
                if not User.select().where(User.code == random_uid).count():
                    uinfo['code'] = random_uid
                    break

        user = User(**uinfo)
        user.save()

    order = None
    # shoptet_shop = Shop.get(name='shoptet')
    # default_shop_id = shoptet_shop.id if shoptet_shop else None
    try:
        order = Order.get(order_shop_id=order_details.get('order_shop_id'))
    except:
        pass  # no order found

    if order and (not update or order.closed):
        return order

    _fields = [d for d in Order._meta.fields]
    order_keys = {key: value for key, value in order_details.items() if key in _fields}
    order_keys.update({k: order_details.get(k) for k in ['order_shop_id', 'order_num']})
    order = Order(**order_keys)
    order.user_id = user.id
    order.save()
    # delete orderlines so that we are sure they are always up-to-date
    # todo find a way to avoid deleting them (compare line by line)
    q = OrderLine.delete().where(OrderLine.order_id == order.id)
    q.execute()
    for order_line in order_details.get('order_lines', []):
        line_dict = process_order_line(order_line)
        line_dict.update({'order_id': order.id})
        ol = OrderLine(**line_dict)
        ol.save()
    if order.close_date is not None and re.match('(Vybavená)|(Pripravená)|(Storno)', order.status):
        order.closed = True
        order.save()
    return order


def make_log(**kwargs):
    log = Log(**kwargs)
    return log.save()


def create_shops():
    shop1 = {'name': 'shoptet', 'web': 'www.bio-market.sk'}
    shop2 = {'name': 'brick-n-mortar', 'city': 'Gotham'}
    for sh in [shop1, shop2]:
        s = Shop(**sh)
        s.save()


def init_db():
    with db:
        db.create_tables([SysUser, User, Shop, Order, OrderLine, Voucher, Log])


if __name__ == '__main__':
    init_db()
    pass
    create_shops()
