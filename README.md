# shoptet-api
Selenium scraping from eshop backend.

As Shoptet does not provide api, in order to automatize our loyalty system 
we need automatic access to eshop data. The data are scraped from web admin
using Selenium framework.
Furthermore we would like to combine the eshop and brick and mortar shop 
loyalty systems into one common system. This will require to create a web app
for loyalty system n shop that will be able to access the eshop data and evaluate
them. 


## INSTALLATION

Clone code from the repository

    `git clone git@github.com:mimmon/shoptet-api.git`

Create virtual environment so that you don't mess your system. Use python3 as an interpreter.

    `virtualenv -p python3 venv`

Activate your environment.

    `. venv/bin/activate`

Install required libraries.

    `pip install -r requirements`


## DEVELOPMENT GUIDELINES

There are not too many guidelines.

- the length of line should be below 120

- PEP8 (space between classes, methods, operators, commas... lambda definitions are allowed)

That's all folks.


## ROADMAP

### Basic tasks

* _**login to admin**_
* _**open order if known link and get info about it**_


### Orders

* INIT: crawl through and index whole site - i.e. we will get url for each order
  This function will be handy if we have to start from scratch
* _**parse orders so that we know the customer, the price and discount info + shipping details**_
* add argument parser so that the program can be used from command line

### DB

* _**integration with db - sqlite3 would be enough (using peewee)**_
* _**create relevant models and convenience methods for easy data manipulation**_
* _**store and use relevant data for faster data fetching**_
* allow updates on records, allow marking finished to deny updates if impossible


### Security

* add check to ~/.shoptet config file, stop program if access rights are not 600 or 400
  (in order to prevent other to see the password)


### Cron jobs

* must be available through PhantomJS or other driver not requiring GUI **!** 
* allow regular checks for new orders (require recording the last updated order)
* automatic evaluation if user should get voucher
* auto create voucher and send to user


### Vouchers

* get voucher status
* _create voucher_
* use voucher in brick shop (=deactivate on in shoptet)
* convert points from brick shop to voucher 


### Client interface

* server based api (flask rest?) to access db from third party apps (django: verne?)



### SHOPTET API

fetch - get from url and save to db (if save=True), return dictionary
get - get from db (and update if fetch=True), return object

`fetch_first_order()`

`fetch_next_order(order=None)`

`fetch_order(id=?, shop_id=?, url=?)`

`get_last_added_order()`

`fetch_next_link(order=None)` - open order in browser and get url of next order, 
        if order is None, use the last added order, if none added, use the very first

`fetch_close_date(order)`: open in browser, click on history and update activity status/close date

logging - create order, update order
