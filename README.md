# shoptet-api
Selenium scraping from eshop backend.

As Shoptet does not provide api, in order to automatize our loyalty system 
we need automatic access to eshop data. The data are scraped from web admin
using Selenium framework.
Furthermore we would like to combine the eshop and brick and mortar shop 
loyalty systems into one common system. This will require to create a web app
for loyalty system n shop that will be able to access the eshop data and evaluate
them. 




## ROADMAP

### Basic tasks

* **login to admin**


### Orders

* INIT: crawl through and index whole site - i.e. we will get url for each order
  This function will be handy if we have to start from scratch
* parse orders so that we know the customer, the price and discount info + shipping details
* add argument parser so that the program can be used from command line

### DB

* integration with db - sqlite3 would be enough (using peewee?)
* store and use relevant data for faster data fetching
* allow updates on records, allow marking finished to deny updates if impossible


### Cron jobs

* must be available through PhantomJS or other driver not requiring GUI **!** 
* allow regular checks for new orders
* automatic evaluation if user should get voucher
* auto create voucher and send to user


### Vouchers

* get voucher status
* _create voucher_
* use voucher in brick shop
* convert points from brick shop to voucher


### Client interface

* server based api (flask rest?) to access db from third party apps (django: verne?)