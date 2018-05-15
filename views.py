import datetime

from flask import request, redirect, url_for, render_template, flash, jsonify
from flask_peewee.utils import get_object_or_404, object_list

from peewee import fn

from shoptet_api.app import app
from shoptet_api.auth import authentification
from shoptet_api.models import SysUser, User, Order, OrderLine, Voucher, Log, Shop
from shoptet_api.utils import make_response, data_to_response

SUBTRACT_CREDIT = 50


# TODO make admin webpage
# TODO inspect urls to create api calls like:
# / :: go to admin page
# /login/ :: POST, get token using credentials
# * /orders/  :: returns all orders
# * /orders/12/  :: returns order 12
# * /orders/12/orderlines/  :: returns order with details
# * /users/   :: returns all users
# * /users/<email>/   :: returns user 22
# * /users/<email>/orders/  ::  returns user 22's orders
# * /users/<email>/orders/discounts/  :: returns user's order with discounts
# /users/<email>/orders/credits/  :: returns credits gained in orders
# /vouchers/   :: returns vouchers with details
# /vouchers/12345678    :: returns specific voucher details

# TODO use endpoints to better url handling
@app.route('/orders/')
def orders():
    orders = Order.select().order_by(Order.id)
    data = [order.serialized for order in orders]
    return data_to_response(data)


@app.route('/orders/<oid>/')
def order_id(oid):
    order = get_object_or_404(Order, Order.id == oid)
    data = order.serialized
    return data_to_response(data)


@app.route('/orders/<oid>/orderlines/')
def order_orderlines(oid):
    order = get_object_or_404(Order, Order.id==oid)
    orderlines = [orderline.serialized for orderline in order.order_lines]
    return data_to_response(orderlines)


@app.route('/users/')
def users():
    users = User.select().order_by(User.email)
    data = [user.serialized for user in users]
    return data_to_response(data)


@app.route('/users/<email>/')
def user_email(email):
    user = get_object_or_404(User, User.email == email)
    data = user.serialized
    return data_to_response(data)


@app.route('/users/<email>/orders/')
def user_orders(email):
    user = get_object_or_404(User, User.email==email)
    orders = [order.serialized for order in user.orders]
    return data_to_response(orders)


@app.route('/users/<email>/orders/discounts/')
def user_discount_orders(email):
    user = get_object_or_404(User, User.email==email)
    discount_orders = [o.serialized for o in user.orders if o.discount and o.discount > 0]
    # discount_orders = [Order.select().join(User).where(
    #                     (User.email == email) &
    #                     ((Order.discount.is_null(False)) | (Order.discount > 0)))
    return data_to_response(discount_orders)


@app.route('/users/<email>/orders/credits/')
def user_credits(email):
    user = get_object_or_404(User, User.email==email)

    plus = Order.select(fn.Count(Order.id)).join(User).where(
                        (User.email == email) &
                        ((Order.discount.is_null(True)) | (Order.discount == 0))).scalar()

    credit = Order.select(fn.Sum(Order.price_applicable)).join(User).where(
                        (User.email == email) &
                        ((Order.discount.is_null(True)) | (Order.discount == 0))).scalar()

    minus = Order.select(fn.Count(Order.id)).join(User).where(
                        (User.email == email) &
                        ((Order.discount.is_null(False)) & (Order.discount > 0))).scalar()

    debit = minus * SUBTRACT_CREDIT

    data = {'user': user.id, 'plus': plus, 'minus': minus,
            'credit': credit, 'debit': debit, 'total': credit - debit}
    return make_response(data)

