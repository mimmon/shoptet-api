#!venv/bin/python
# -*- coding: utf-8 -*-
import re
from selenium import webdriver
from selenium.webdriver.common.by import By

BASE_URL = 'YOUR-URL'
ADMIN_URL = BASE_URL + 'admin/'
LOGIN_URL = ADMIN_URL + 'login/'

# CREDENTIALS: TODO READ FROM SYMLINK
EMAIL = 'EMAIL'
PASSWORD = 'PASSWORD'

def get_credentials():
    return {'email': EMAIL, 'password': PASSWORD}


class ShoptetBrowsing:
    browser = None

    def __init__(self):
        self.browser = webdriver.Firefox()
        # browser = webdriver.PhantomJS()

    def find_pattern(self, pattern, get_one=False):
        found = re.findall(pattern, self.browser.page_source)
        if get_one and found:
            return found[0]
        return found

    def login(self):

        self.browser.get(ADMIN_URL)
        # tokens = re.findall(r'shoptet.csrfToken = "(?P<token>.+)";', browser.page_source)
        # csrf_token = tokens and tokens[0] or None

        el = self.browser.find_element('name', 'email')
        el.send_keys(EMAIL)

        el = self.browser.find_element('name', 'password')
        el.send_keys(PASSWORD)

        el = self.browser.find_element(By.XPATH, '//input[@class="fake-submit"]')
        el.click()

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

        max_page = self.find_pattern(
            r'<a href=.+title="Posledná stránka".+>(?P<max_page>\d)</a>',
            get_one=True)
        return max_page

    def get_order_link(self, order_num):
        pass

    def get_page_extreme_orders(self, page_num=None, reload=True):
        if reload:
            self.get_order_page(page_num)
        tbody = self.browser.find_element(
            By.XPATH, "//div[@class='table-holder']/table/tbody")


    def get_order(self, order_number):
        pass
        # el = self.browser.find_element(By.XPATH, "//a[@href='/admin/objednavky/']")
        # el.click()
        #
        # el = self.browser.find_element(By.XPATH, "//a[@href='/admin/prehlad-objednavok/']")
        # el.click()

        # browser.get('https://www.bio-market.sk/admin/')

if __name__ == '__main__':
    sh = ShoptetBrowsing()
    sh.login()
    sh.get_order_page(3)
    sh.get_max_page()
    pass
