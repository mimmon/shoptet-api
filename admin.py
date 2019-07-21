import datetime
from flask import request, redirect

from flask_peewee.admin import Admin, ModelAdmin, AdminPanel
from flask_peewee.filters import QueryFilter

from app import app, db
from auth import authentification
from models import User, Order, Log, Voucher, Shop, SysUser


admin = Admin(app, authentification, branding='Example Site')


class UserAdmin(ModelAdmin):
    columns = ('email', 'name', 'last_name',)
    # foreign_key_lookups = {'user': 'email'}
    # filter_fields = ('user', 'content', 'pub_date', 'user__username')


class OrderAdmin(ModelAdmin):
    columns = ('user_id', 'order_num', 'open_date', 'close_date', 'total_price')
    # exclude = ('created_date',)


class LogAdmin(ModelAdmin):
    columns = ('log_time', 'event', 'model', 'record', 'user_id', 'details')


authentification.register_admin(admin)
admin.register(User, UserAdmin)
admin.register(Order, OrderAdmin)
admin.register(Log, LogAdmin)
