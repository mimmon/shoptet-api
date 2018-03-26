#!venv/bin/python
# -*- coding: utf-8 -*-
import logging
from lxml import etree, html
import os
import re
from selenium import webdriver
from selenium.webdriver.common.by import By

_logger = logging.getLogger(__name__)

CONFIG_FILE = '/home/mimmon/.shoptet'

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


config = parse_config(CONFIG_FILE)

BASE_URL = config.get('BASE_URL', 'YOUR-URL')
BASE_URL = BASE_URL + (os.sep if not BASE_URL.endswith(os.sep) else '')
ADMIN_URL = BASE_URL + 'admin/'
LOGIN_URL = ADMIN_URL + 'login/'

EMAIL = config.get('EMAIL', 'EMAIL')
PASSWORD = config.get('PASSWORD', 'PASSWORD')

ORDER_LINK = ADMIN_URL + 'objednavky-detail/?id={order_id}'


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


class Shoptet:
    browser = None
    logged_in = None

    def __init__(self):
        self.browser = webdriver.Firefox()
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

        # browser.get('https://www.bio-market.sk/admin/')

    def get_order_page(self, page_num=None):
        if page_num is None:
            page_num = 1
        appendix = ('?from=%d' % page_num) if page_num > 1 else ''
        url = ADMIN_URL + 'prehlad-objednavok/%s' % appendix
        self.browser.get(url)

    def get_max_page(self):
        self.get_order_page()

        max_page = 1
        last_link = self.find_by_xpath("//a[@title='Posledná stránka']")
        if last_link:
            max_page = int(getattr(last_link, 'text', 0))
        return max_page

    def browse_orders(self, page_num=None):
        if page_num:
            self.get_order_page(page_num)
        # browse orders on page
        # wip - this only get the first one
        # self.browser.find_element(By.CSS_SELECTOR, "tr[id*='rowId-']")
        # html = etree.parse(self.browser.page_source, parser=etree.HTMLParser(remove_comments=True))
        doc = html.document_fromstring(self.browser.page_source)
        order_ids = map(int, self.find_pattern('<tr id="rowId-(?P<order_id>\d+)'))
        sorted_list = sorted(order_ids)

        for order_id in sorted_list:
            row = doc.get_element_by_id('rowId-{}'.format(order_id))
            a = row.find('td/a[@title="Detail objednávky"]')
            url = a.attrib.get('href')
            order_num = a.text
            customer_name = row.find('td/div/div[@class="order-customer"]').text.strip()

            print('ORDER {}: {}'.format(order_num, customer_name))


    def get_order(self, order_number):
        pass


    def get_order_from_link(self, order_id):
        if not self.logged_in:
            self.login()

    @login_required
    def get_last_order_id(self):
        self.get_order_page()
        last_order_id = sh.find_pattern('<tr id="rowId-(?P<order_id>\d+)', get_first=True)
        print('last_order %s' % last_order_id)
        return int(last_order_id)


if __name__ == '__main__':
    sh = Shoptet()
    sh.login()
    max_page = sh.get_max_page()
    sh.browse_orders(max_page)

    # TO BE UNCOMMENTED WHEN DB IS FINISHED
    # for page in range(max_page, 0):
    #     sh.browse_orders(page)
    sh.get_last_order_id()

    pass


## ADD ARGUMENT PARSER

## SPLIT TO VARIOUS FUNCTIONS

#### parse orders + write to db
#### get a single order detail + make it parse through all of them
#### parse vouchers
#### check voucher

