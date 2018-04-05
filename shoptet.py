#!venv/bin/python
# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup
from decimal import Decimal
import logging
from lxml import etree, html
import os
import re
from selenium import webdriver
from selenium.webdriver.common.by import By

from .utils import *

_logger = logging.getLogger(__name__)

CONFIG_FILE = '/home/mimmon/.shoptet'
config = parse_config(CONFIG_FILE)

BASE_URL = config.get('BASE_URL', 'YOUR-URL')
BASE_URL = BASE_URL + (os.sep if not BASE_URL.endswith(os.sep) else '')
ADMIN_URL = BASE_URL + '/admin'
LOGIN_URL = ADMIN_URL + '/login'

EMAIL = config.get('EMAIL', 'EMAIL')
PASSWORD = config.get('PASSWORD', 'PASSWORD')

ORDER_LINK = ADMIN_URL + 'objednavky-detail/?id={order_id}'


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

    @login_required
    def get_order_from_link(self, url, save=False):
        """Open url and scrape the order, optionally store to database"""
        if not url:
            _logger.warning('No url for order %s', order)
            return None

        order_details = {}
        shop.browser.get(BASE_URL + url)
        soup = BeautifulSoup(self.browser.page_source, 'html5lib')

        # CONTACT
        uinfo = order_details.setdefault('user_info', {})
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

        order_details.setdefault('order_lines', [])
        # we need to save total price, transport price, plain price, discount applied
        # all of them including and excluding vat

        # postage/transport prices have no status and no code
        # discount
        # total price with and without vat can be taken from summary below order
        div_total_price = soup.find('div', {'class': 'total-price'})
        for line in filter_contents(div_total_price):
            for keyword, content, contra in [
                    ('no_vat_price', 'Cena bez DPH:', None),
                    ('vat', 'DPH:', 'Cena bez DPH:'),
                    ('total_price', 'Čiastka k úhrade:', None)]:
                # total price is not navigable string, but Tag (<big>)
                if not isinstance(line, str):
                    line = line.contents[0]
                if content in line and (contra is None or contra not in line):
                    order_details[keyword] = strip_price(line, content)
                    break

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
            p_amount = handle_contents(tds[4], lambda x: len(x.split()) > 1 and x.split()[0] else x)
            p_unit_price = handle_content_price(tds[5])
            p_discount_percent = handle_contents(
                tds[6], lambda x: x.span.text.strip().rstrip(' %'), Decimal)
            p_vat_percent = handle_contents(
                tds[7], lambda x: x.strip().rstrip('%'), Decimal)
            p_total_vat_including = handle_content_price(tds[8])
            p_del = handle_contents(tds[9])

            # todo store product lines and purchases for further analysis
            # first step requires distinguishing between products and services
            # (postage, pay-on-delivery)
            # services are "products" with no code, image and status
            # services should be negative - that is reserved for total_discount
            order_details['order_lines'].append({
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

        # TODO create function in utils using peewee ORM
        # if save:
        #     save_order(order_details)

        return order_details

    def get_order(self, order_number, save=False):
        """Get link from DB and call get_order_from_link, optionally store to database"""
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

    def get_user_by_email(self):
        # get from db
        pass


if __name__ == '__main__':
    shop = Shoptet()
    shop.login()
    max_page = shop.get_max_page()
    orders = shop.browse_orders(max_page)

    for order in orders[:5]:
        url = order.get('order_url')
        print(url)
        shop.get_order_from_link(url)
    # TO BE UNCOMMENTED WHEN DB IS FINISHED
    # for page in range(max_page, 0):
    #     sh.browse_orders(page)
    shop.get_last_order_id()

    pass


## ADD ARGUMENT PARSER

## SPLIT TO VARIOUS FUNCTIONS

#### parse orders + write to db
#### get a single order detail + make it parse through all of them
#### parse vouchers
#### check voucher

