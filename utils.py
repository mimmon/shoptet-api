from decimal import Decimal
import logging

try:
    from .models import User, Order, OrderLine
except SystemError:
    from models import User, Order, OrderLine

_logger = logging.getLogger(__name__)


def parse_config(filename):
    # KEY=VALUE
    # left side of the first = is key, the rest is value, may contain =s
    result = {}
    with open(filename, 'r') as f:
        for line in filter(lambda x: '=' in x, f.readlines()):
            try:
                key, value = line.split('=', 1)
                result[key.strip()] = value.strip()
            except ValueError:
                # skip line
                _logger.info('skipping invalid line: %s', line)
    return result


def get_credentials():
    conf = parse_config('~/.shoptet')
    return {k: v for k, v in conf.items() if k.lower() in ['email', 'password']}


def login_required(func):
    """
    Checks if user is logged in.
    If not, login will precede the method execution.
    """
    def wrapper(*args, **kwargs):
        self = args[0]
        if not self.logged_in:
            self.login()
        return func(*args, **kwargs)
    return wrapper


def handle_element(elem, args, func=None, func2=None):
    """
    A helper function to handle elements from BeautifulSoup element.find()
    :param elem: BeautifulSoup Tag (element)
    :param args: args tuple for find method. String can be used for a single
            arg, otherwise tuple
    :param func: ad hoc function used to manipulate found element
    :param func2: outer function, may be used to convert the result found in
            the process
    :return: content of found element processed by func or None if not found
    """
    if elem is None:
        return elem
    if isinstance(args, str):
        found = elem.find(args)
    elif isinstance(args, (tuple, list)):
        found = elem.find(*args)
    else:
        found = elem
    if not found:
        return None
    if not func or not callable(func):
        if not callable(func):
            _logger.warning('%s not callable', func)
        return found
    _found = func(found)
    if not func2 or not callable(func2):
        return _found
    try:
        return func2(_found)
    except ValueError:
        return _found


def handle_contents(elem, func=None, func2=None):
    """
    Helper function to extract data from a single line / unstructure entry
    :param elem: BeautifulSoup Tag (element)
    :param func: ad hoc function used to manipulate content
    :param func2: outer function, may be used to convert the result
    :return: content of content processed by func or None if not found
    """
    return handle_element(elem.contents[0].strip(), None, func, func2)


def handle_content_price(elem, clean=None):
    if clean is not None and callable(clean):
        elem = clean(elem)
    return handle_contents(
        elem, lambda x: x.lstrip('€').replace(',', '.'), Decimal)


def handle_price(line, clean=None):
    if clean is not None and callable(clean):
        line = clean(line)
    price = line.lstrip('€').replace(',', '.')
    try:
        return Decimal(price)
    except ValueError:
        return None


def strip_price(line, strip_string=None):
    line = line.strip()
    if strip_string:
        line = line.strip(strip_string).strip()
    price = line.lstrip('€').replace(',', '.')
    try:
        return Decimal(price)
    except ValueError:
        return None


def filter_contents(elem):
    f = lambda x: isinstance(x, str) or getattr(x, 'name', None) != 'br'
    for i in filter(f, elem.contents):
        yield i
