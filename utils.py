from decimal import Decimal
import logging
import re
from peewee import *
# from peewee import Expression  # the building block for expressions


try:
    from .models import User, Order, OrderLine
except SystemError:
    from models import User, Order, OrderLine

_logger = logging.getLogger(__name__)

# def is_max(lhs, rhs=None):
#     return Expression(lhs, '==', rhs)


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


def handle_contents(elem, func=None, func2=None, recursive=False, contents=True):
    """
    Helper function to extract data from a single line / unstructure entry
    :param elem: BeautifulSoup Tag (element)
    :param func: ad hoc function used to manipulate content
    :param func2: outer function, may be used to convert the result
    :return: content of content processed by func or None if not found
    """
    if not func:
        func = lambda x: x
    _elem = elem
    if contents:
        _elem = elem.contents[0].strip()
    try:
        result = handle_element(_elem, None, func, func2)
    except AttributeError:
        if not contents:
            _elem = elem.contents[0].strip()
            result = handle_element(_elem, None, func, func2)
    if not recursive or result:
        return result
    for line in elem.contents:
        try:
            # return first none empty  # todo improve this method
            return handle_element(line.contents[0].strip(), None, func, func2)
        except:
            continue
        return None


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


def get_last_order():
    select = Order.select().where(Order.shop_order_id == Order.select(fn.Max(Order.shop_order_id)).scalar())
    return select[0] if select.count() else None


def get_status_from_soup(soup):
    status_id = soup.find('select', {'id': 'status-id'})
    if not status_id:
        return None
    option = status_id.find('option', {'selected': 'selected'})
    if not option:
        return None
    return option.text


def get_user_info_from_soup(soup):
    # CONTACT
    uinfo = {}
    email = None
    contact = soup.find('td', {'id': 'customer-contact'})
    try:
        email = contact.p.a['href'].split(':', 1)[1]
    except:
        _logger.info('Email cannot be found')
    uinfo.update({'email': email})

    phone = None
    for line in filter(lambda x: 'Telefón' in x, contact.p.contents):
        phones = re.findall('Telefón: *(\d+)?', line)
        if phones:
            phone = phones[0]
            break
    uinfo.update({'phone': phone})

    # BILLING
    billing = soup.find('td', {'id': 'billing-address'})
    name_element = billing.find('a', {'title': 'Detail zákazníka'})
    name = name_element.text if name_element else None
    uinfo.update({'name': name})

    # as the address in order details is stored as (more or less) plain text
    # in this version of program it will be ignored
    # in the future there can be a  individual scraper for users only
    # users may be identified by email
    # if save:
    #     User.get()
    #       if not user:
    #             create_user()
    #       Order.get()
    #         if not order:
    #           create_order()
    #         else:
    #            update_order()

    ##############################################################
    # MISSING PARAMS
    # street = CharField(null=True)
    # zip = CharField(null=True)
    # city = CharField(null=True)
    # country = CharField(null=True)
    # phone = CharField(null=True)

    return uinfo


def get_orderlines_from_soup(soup):
    orderlines = []
    table = soup.find('table', {'class': 'std-table-listing'})
    # todo add mapping from thead
    for tr in table.tbody.find_all('tr'):
        # for now we ignore individual items
        # this iteration is to determine postage and transport prices
        tds = tr.find_all('td')
        p_code = handle_element(tds[0], 'a', lambda x: x.text.strip())
        p_img = handle_element(tds[1], 'img', lambda x: x['src'])
        p_description = handle_element(tds[2], 'span', lambda x: x.text)
        p_status = handle_contents(tds[3])
        # todo add units to amount
        p_amount = handle_contents(tds[4],
                                   lambda x: len(x.split()) > 1 and x.split()[0] or x,
                                   recursive=True)
        p_unit_price = handle_content_price(tds[5])
        p_discount_percent = handle_contents(
            tds[6], lambda x: x.span.text.strip().rstrip(' %'), Decimal, contents=False)
        p_vat_percent = handle_contents(
            tds[7], lambda x: x.strip().rstrip('%'), Decimal)
        p_total_vat_including = handle_content_price(tds[8])
        p_del = handle_contents(tds[9])

        # todo store product lines and purchases for further analysis
        # first step requires distinguishing between products and services
        # (postage, pay-on-delivery)
        # services are "products" with no code, image and status
        # services should be negative - that is reserved for total_discount
        orderlines.append({
            'code': p_code,
            'img': p_img,
            'description': p_description,
            'status': p_status,
            'amount': p_amount,
            'unit_price': p_unit_price,
            'discount_percent': p_discount_percent,
            'vat_percent': p_vat_percent,
            'total_vat_including': p_total_vat_including,
        })
    return orderlines
