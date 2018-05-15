from flask_peewee.rest import RestAPI, RestResource, UserAuthentication, AdminAuthentication, RestrictOwnerResource

from shoptet_api.app import app
from shoptet_api.auth import authentification
from shoptet_api.models import User, Order, OrderLine, Voucher, Log, Shop


user_auth = UserAuthentication(authentification)
admin_auth = AdminAuthentication(authentification)

# instantiate our api wrapper
api = RestAPI(app, default_auth=user_auth)


class UserResource(RestResource):
    # exclude = ('password', 'email',)
    pass

class OrderResource(RestResource):
    # owner_field = 'user'
    include_resources = {'user_id': UserResource}


class OrderLineResource(RestResource):
    include_resources = {'order_id': OrderResource}


class LogResource(RestResource):
    pass
    # include_resources = {
    #     'from_user': UserResource,
    #     'to_user': UserResource,
    # }
    # paginate_by = None

class ShopResource(RestResource):
    pass

class VoucherResource(RestResource):
    pass

# register our models so they are exposed via /api/<model>/
api.register(User, UserResource, auth=admin_auth)
api.register(Order, OrderResource)
api.register(OrderLine, OrderLineResource)
api.register(Log, LogResource)
api.register(Voucher, VoucherResource)
api.register(Shop, ShopResource)
