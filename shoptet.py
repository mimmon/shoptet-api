#!venv/bin/python
# -*- coding: utf-8 -*-
import argparse
from bs4 import BeautifulSoup
import datetime
from decimal import Decimal
import logging
from lxml import html
import os
import re
import sys
from peewee import *
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities


try:
    from .utils import *
except (ImportError, SystemError):
    from utils import *
try:
    from .models import save_order, make_log
except (ImportError, SystemError):
    from models import save_order, make_log

_logger = logging.getLogger(__name__)

CONFIG_FILE = '/home/mimmon/.shoptet'
config = parse_config(CONFIG_FILE)

BASE_URL = config.get('BASE_URL', 'YOUR-URL')
BASE_URL = BASE_URL + (os.sep if not BASE_URL.endswith(os.sep) else '')
ADMIN_URL = BASE_URL + '/admin'
LOGIN_URL = ADMIN_URL + '/login'

ORDERS_URL = '/admin/objednavky/'
ORDERS_OVERVIEW_URL = '/admin/prehlad-objednavok/'
VOUCHERS_PAGE_URL = '/admin/zlavove-kupony/'

EMAIL = config.get('EMAIL', 'EMAIL')
PASSWORD = config.get('PASSWORD', 'PASSWORD')

ORDER_LINK = '/admin/objednavky-detail/?id={order_id}'

MAX_UPDATE_LIMIT = 50


class Shoptet:
    browser = None
    logged_in = None

    def __init__(self):
        cap = DesiredCapabilities.FIREFOX
        cap['marionette'] = True
        self.browser = webdriver.Firefox(capabilities=cap)
        # self.browser = webdriver.Chrome('/home/mimmon/project/shoptet/drivers/chromedriver')
        # browser = webdriver.PhantomJS()

    def find_pattern(self, pattern, get_first=False):
        found = re.findall(pattern, self.browser.page_source)
        if get_first and found:
            return found[0]
        return found

    def find_by_xpath(self, xpath):
        return self.browser.find_element(By.XPATH, xpath)

    def find_by_css(self, selector):
        return self.browser.find_element(By.CSS_SELECTOR, selector)

    def login(self):
        self.browser.get(ADMIN_URL)
        # tokens = re.findall(r'shoptet.csrfToken = "(?P<token>.+)";', browser.page_source)
        # csrf_token = tokens and tokens[0] or None

        el = self.browser.find_element('name', 'email')
        el.send_keys(EMAIL)

        el = self.browser.find_element('name', 'password')
        el.send_keys(PASSWORD)

        el = self.browser.find_element(By.XPATH, '//a[@href=\"#\"]')
        el.click()

        self.logged_in = True

    def get_orders(self):
        el = self.browser.find_element(By.XPATH, "//a[@href='/admin/objednavky/']")
        el.click()

        el = self.browser.find_element(By.XPATH, "//a[@href='/admin/prehlad-objednavok/']")
        el.click()

    def get_order_page(self, page_num=None):
        if page_num is None:
            page_num = 1
        appendix = ('?from=%d' % page_num) if page_num > 1 else ''
        url = ADMIN_URL + '/prehlad-objednavok/%s' % appendix
        self.browser.get(url)

    def get_max_page(self):
        self.get_order_page()

        max_page = 1
        last_link = self.find_by_xpath("//a[@title='Posledná stránka']")
        if last_link:
            max_page = int(getattr(last_link, 'text', 0))
        return max_page

    @login_required
    def browse_orders(self, page_num=None):
        if page_num:
            self.get_order_page(page_num)
        # browse orders on page
        # wip - this only get the first one
        # self.browser.find_element(By.CSS_SELECTOR, "tr[id*='rowId-']")
        # html = etree.parse(self.browser.page_source, parser=etree.HTMLParser(remove_comments=True))
        # TODO refactor using BeautifulSoup
        doc = html.document_fromstring(self.browser.page_source)
        order_ids = map(int,
                        self.find_pattern('<tr id="rowId-(?P<order_id>\d+)'))
        sorted_list = sorted(order_ids)

        orders = []

        for order_id in sorted_list:
            row = doc.get_element_by_id('rowId-{}'.format(order_id))
            a = row.find('td/a[@title="Detail objednávky"]')
            url = a.attrib.get('href')
            order_num = a.text
            customer_name = row.find(
                'td/div/div[@class="order-customer"]').text.strip()

            print('ORDER {}: {}'.format(order_num, customer_name))

            orders.append({'order_number': order_num, 'order_id': order_id, 'order_url': url})

        return orders

    def get_next_url_from_soup(self, soup):
        url = soup.find('a', {'class': 'ico-next'})
        href = url.attrs.get('href', '')
        href = href.strip('&controllerReferer=')
        return href

    def get_next_url(self, order=None):
        if order is None:
            order = get_last_order()
        if not order.url:
            order.url = ORDER_LINK.format(**{'order_id': order.shop_order_id})
            order.save()

        shop.browser.get(BASE_URL + order.url)
        soup = BeautifulSoup(self.browser.page_source, 'html5lib')
        return self.get_next_url_from_soup(soup)

    @login_required
    def open_order_from_url(self, url):
        """Open url with order"""
        if not url:
            _logger.warning('No url for order.')
            return None

        _logger.info('Read order from %s', url)
        shop.browser.get(BASE_URL + url)
        soup = BeautifulSoup(self.browser.page_source, 'html5lib')
        return soup

    @login_required
    def read_order_from_url(self, url):
        """Open url and scrape the order, return structured data"""
        soup = self.open_order_from_url(url)

        if soup is None:
            return None

        order_details = {}
        # order details and order num can be received in other place of code
        # this is to ensure we can get those independently from sheer url
        r = re.search(r'\?id=(?P<order_id>\d+)', url)
        order_details['shop_order_id'] = r.group('order_id') if r else None
        # todo handle last order!
        order_details['order_num'] = soup.h1.strong.text
        order_details['url'] = url
        order_details['next_url'] = self.get_next_url_from_soup(soup)

        open_date = None
        raw_open_date = soup.find_all('span', {'id': 'order-date'})
        if raw_open_date:
            open_date = datetime.datetime.strptime(raw_open_date[0].text, '(%d.%m.%Y %H:%M:%S)')
        order_details['open_date'] = open_date

        # todo decide if choices are used or plain text from web
        status = get_status_from_soup(soup)
        if status:
            order_details['status'] = status

        # .. close_date = DateField(null=True)                  # todo this can be found in another page, not critical,
        #                                                       # will be resolved later

        uinfo = get_user_info_from_soup(soup)
        order_details['user_info'] = uinfo

        # we need to save total price, transport price, plain price, discount applied
        # all of them including and excluding vat
        # postage/transport prices have no status and no code
        # total price with and without vat can be taken from summary below order
        div_total_price = soup.find('div', {'class': 'total-price'})
        for line in filter_contents(div_total_price):
            for keyword, content, contra in [
                    ('price_no_vat', 'Cena bez DPH:', None),
                    ('vat', 'DPH:', 'Cena bez DPH:'),
                    ('total_price', 'Čiastka k úhrade:', None)]:
                # total price is not navigable string, but Tag (<big>)
                if not isinstance(line, str):
                    line = line.contents[0]
                if content in line and (contra is None or contra not in line):
                    order_details[keyword] = strip_price(line, content)
                    break

        # get order lines
        order_lines = get_orderlines_from_soup(soup)
        order_details['order_lines'] = order_lines

        discount = Decimal('0.0')
        for orderline in order_details['order_lines']:
            pc = orderline.get('discount_percent', Decimal('0.0'))
            if pc:
                discount += orderline.get('total_vat_including') * pc / (100 - pc)
        order_details['discount'] = discount

        # shipping costs
        total = 'total_vat_including'
        services_lines = [line for line in order_lines if line['code'] is None]
        shipping_lines = [line for line in services_lines if line[total] >= 0]
        discount_lines = [line for line in services_lines if line[total] < 0]
        shipping_cost = sum(line[total] for line in shipping_lines)
        order_details['discount'] += sum(line[total] for line in discount_lines)

        plain_price = order_details['total_price'] - shipping_cost
        # price applicable for loyalty system - only if no discount applied
        # add rules for applicable price - so that they are consistnent if system changes
        # todo find out why this does not work anymore!!
        order_details['price_applicable'] = plain_price if not discount else Decimal('0.00')
        order_details['shipping_cost'] = shipping_cost
        order_details['shipping'] = ';'.join(ln['description'] for ln in shipping_lines)
        # todo discount voucher has no code but it is not shipping related
        # get_close_date()
        close_date = self.read_last_order_update()
        if close_date:
            order_details['close_date'] = close_date

        return order_details

    @login_required
    def fetch_order_from_url(self, url, update=True):
        """Open url and scrape the order, optionally store to database"""
        if not url:
            _logger.warning('No url for order.')
            return None

        try:
            order_details = self.read_order_from_url(url)
        except AttributeError:  # reads from empty order site, does not find ceratin element
            return None

        order = save_order(order_details, update=update)

        # make log
        loginfo = {'event': 'create', 'model': 'order', 'record': order.id}
        make_log(**loginfo)
        return order

    def get_order(self, **kwargs):
        """Get link from DB using id, shop_order_id, order_num..."""
        pass

    @login_required
    def get_last_order_id(self):
        self.get_order_page()
        last_order_id = self.find_pattern('<tr id="rowId-(?P<order_id>\d+)', get_first=True)
        print('last_order %s' % last_order_id)
        return int(last_order_id)

    @login_required
    def get_user_by_id(self):
        pass

    def get_user_by_email(self, email):
        try:
            return User.get(User.email == email)
        except DoesNotExist:
            return None

    def fetch_first_order(self):
        max_page = self.get_max_page()
        orders = self.browse_orders(max_page)
        url = orders[0].get('order_url')
        order = shop.fetch_order_from_url(url)

        oid = order.id if isinstance(order, Order) else None
        loginfo = {'event': 'create', 'model': 'order', 'record': oid}
        make_log(**loginfo)

        return order

    def read_last_order_update(self, url=None):
        if url is not None:
            self.open_order_from_url(url)

        el = self.browser.find_element(By.XPATH, '//a[@href=\"#t3\"]')
        el.click()

        td = self.browser.find_element(By.XPATH, '//div[@id=\"t3\"]//table//td')
        close_date = None
        if td:
            close_date = datetime.datetime.strptime(td.text, '%d.%m.%Y %H:%M:%S')

        el = self.browser.find_element(By.XPATH, '//a[@href=\"#t1\"]')
        el.click()

        return close_date

    def get_last_added_order(self):
        pass

    def get_next_order(self, order=None):
        # get last updated and get the next_one
        if order is None:
            order = self.get_last_added_order()
        if order is None:
            return self.get_first_order()
        url = self.get_next_link(order)
        return self.get_order_from_link(url) if url else None

    def update_active_orders(self):
        # filter active orders and update their status
        pass

    def get_vouchers_page(self):
        el = self.browser.find_element(By.XPATH, "//a[@href='/admin/marketing/']")
        el.click()
        el = self.browser.find_element(By.XPATH, "//a[@href='/admin/zlavove-kupony/']")
        el.click()

    @login_required
    def generate_vouchers(self, amount=1, expiration_days=550, discount_percent=10):
        # will generate <amount> vouchers that will expire at <expiration>
        self.get_vouchers_page()
        el = self.browser.find_element(By.XPATH, '//a[@href=\"/admin/zlavove-kupony-detail/\"]')
        el.click()

        el = self.browser.find_element(By.XPATH, '//label[@for=\"add-more-coupons\"]')
        el.moveTo
        el.click()

        el = self.browser.find_element(By.XPATH, '//select[@id=\"coupon-count\"]')
        el.click()
        el = self.browser.find_element(By.XPATH, '//option[@value=\"{}\"]'.format(amount))
        el.click()
        el = self.browser.find_element(By.XPATH, '//select[@id=\"discount-type\"]')
        el.click()
        el = self.browser.find_element(By.XPATH, '//option[@value=\"percentual\"]'.format(amount))
        el.click()
        el = self.browser.find_element(By.XPATH, '//select[@id=\"discount-amount\"]')
        el.send_keys(discount_percent)

        _from = datetime.date.today()
        _until = _from + datetime.timedelta(days=expiration_days)
        valid_from = _from.strftime('%-d.%-m.%Y')
        valid_until = _until.strftime('%-d.%-m.%Y')
        el = self.browser.find_element(By.XPATH, '//select[@id=\"valid-from\"]')
        el.send_keys(valid_from)
        el = self.browser.find_element(By.XPATH, '//select[@id=\"valid-until\"]')
        el.send_keys(valid_until)

        el = self.browser.find_element(By.XPATH, '//input[@class=\"fake-submit\"]')
        # <input value="" class="fake-submit" type="submit">
        # <a href="/admin/zlavove-kupony-detail/" title="Pridať" class="btn btn-md btn-default button-add no-disable">Pridať</a>
        # <input name="addMoreCoupons" id="add-more-coupons" value="1" data-label-adjusted="true" type="radio">


class Namespace:
    pass


class Parser:

    def __init__(self):
        self.program = sys.argv[0]
        self.sys_argv = sys.argv[1:]
        self.namespace = Namespace()

    def argument_validator(self):
        """checks arguments of a command"""
        result = []
        if self.handler == 'order':
            pass
        if self.handler == 'voucher':
            if self.command == 'create':
                if not self.namespace.args:
                    result = 0
                else:
                    error_message = '<voucher create NUM> if NUM either it defaults to 0 '\
                                    'otherwise must be a non negativeinteger smaller than 501.'
                    try:
                        result = int(self.args[0])
                    except:
                        raise argparse.ArgumentTypeError(error_message)
                    else:
                        if not 0 <= result < 501:
                            raise argparse.ArgumentTypeError(error_message)
        return result

    def parse_arguments(self):
        parser = argparse.ArgumentParser(description='Shoptet API')

        handlers = ['order', 'voucher']
        parser.add_argument('domain', type=str, choices=handlers,
                            help='An entity you want to work with {order | voucher}')

        order_commands = ['update', 'status']
        voucher_commands = ['create', 'invalidate', 'count', 'status']
        available_commands = order_commands + voucher_commands
        parser.add_argument('command', type=str, help='Command to perform',
                            choices=available_commands)
        parser.add_argument('args', nargs='*', type=self.argument_validator)

        self.namespace = parser.parse_args(self.sys_argv)

        return self.namespace


if __name__ == '__main__':

    p = Parser()
    arguments = p.parse_arguments()

    if arguments.domain == 'order':

        shop = Shoptet()
        shop.login()

        if not Order.select().count():
            shop.fetch_first_order()

        if arguments.command == 'update':   # -u
            updated = 0
            next_url = None
            while MAX_UPDATE_LIMIT and updated < MAX_UPDATE_LIMIT:
                url = next_url or shop.get_next_url()
                order = shop.fetch_order_from_url(url)
                try:
                    next_url = order.next_url
                except AttributeError:
                    break
                else:
                    updated += 1
                    if not next_url:
                        break

    elif arguments.domain == 'voucher':

        shop = Shoptet()
        shop.login()

        if arguments.command == 'create':
            amount = arguments.args[0] if arguments.args else 0
            shop.generate_vouchers(amount)


    # max_page = shop.get_max_page()
    # orders = shop.browse_orders(max_page)
    #
    # for order in orders[:20]:
    #     url = order.get('order_url')
    #     print(url)
    #     shop.get_order_from_link(url, save=True)
    # # TO BE UNCOMMENTED WHEN DB IS FINISHED
    # # for page in range(max_page, 0):
    # #     sh.browse_orders(page)
    # shop.get_last_order_id()
    #
    # pass

# TODO make functions that will continue with next order
# make a log record according to which we will find the last written order and then continue
# make flag on order so taht we know it is already closed and we do not have to deal with it


## ADD ARGUMENT PARSER

## SPLIT TO VARIOUS FUNCTIONS

#### parse orders + write to db
#### get a single order detail + make it parse through all of them
#### parse vouchers
#### check voucher
# TODO move requirements into git repo
