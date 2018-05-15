class Configuration(object):
    DATABASE = {
        'name': 'shoptet.db',
        'engine': 'peewee.SqliteDatabase',
        'check_same_thread': False,
    }
    DEBUG = True
    SECRET_KEY = 'replace-this'
