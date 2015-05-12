#!/usr/local/bin/python3

from bs4 import BeautifulSoup
from random import randint
from time import sleep
from datetime import datetime
import re
import requests
import xlsxwriter

# Yelp Scraper v0.0.1 2015-05-06
# DESCRIPTION : This program allows to browse Yelp France results to extract
# (scrap) desired informations.

# -----------------------------------------------------------------------------
# ---------------------------------- CONFIG -----------------------------------
# -----------------------------------------------------------------------------

# -- Functional configuration
CITY = "Paris"
# Districts are optionnals but override CITY if written
PARIS_DISTRICTS = ["Grands_Boulevards/Sentier", "Châtelet/Les_Halles"]
# Can be one of Yelp cflt (check yelp.fr to list them)
CFLTS = [
    # food
    "bagels", "sandwiches", "burgers", "hotdogs", "icecream", "desserts",
    "cupcakes", "juicebars", "friterie",
    # beautysvc
    "tanning", "hair", "hair_extensions", "othersalons", "massage",
    "eroticmassage", "piercing", "eyelashservice", "skincare", "spas",
    "hairremoval"]

# -----------------------------------------------------------------------------

# -- Technical configuration
DEBUG = False # If True, won't parse Yelp URL but HTML test document
MAX_SLEEP = 30000 # in milliseconds

# -----------------------------------------------------------------------------
# ---------------------------- CLASSES / FUNCTIONS ----------------------------
# -----------------------------------------------------------------------------

class YelpShop(object):
    ''' Used to store desired informations about a Yelp shop '''

    def __init__(self, name="", address="", zipcode="", district="", phone="",
                 url="", categories=[]):
        self.name = name
        self.address = address
        self.zipcode = zipcode
        self.district = district
        self.phone = phone
        self.url = url # Url
        self.categories = categories # WARN : Textuals categories <> cflt

    def __str__(self):
        return "{0} ({1})".format(self.name, self.phone)

def mylog(msg):
    ''' Personalized print() tool, used for dummy logging '''
    print("-- " + msg)

def page_to_index(page_num):
    ''' Transforms page number into start index to be written in Yelp URL '''
    return (page_num - 1)*10

def build_arglist(elts):
    ''' Return a Yelp url-friendly string created from a Python list'''

    res = "["
    for elt in elts[:-1]:
        res += elt + ","
    res += elts[-1] + "]"

    return res

def build_yelp_url(page, c):
    ''' Builds Yelp URL for the given page and cflt to be parsed according to
    config variables '''

    url = "http://www.yelp.fr/search?&start={0}".format(page_to_index(page))
    if CITY:
        url += "&find_loc={0}".format(CITY)
    url += "&cflt={0}".format(c) # We assume that CFLTS list is not empty
    if PARIS_DISTRICTS:
        url += "&l=p:FR-75:Paris::{0}".format(build_arglist(PARIS_DISTRICTS))

    return url

def extract_zipcode(adr):
    ''' get a zipcode in the middle of an address '''

    try:
        res = re.compile('\d{5}').findall(adr)[0] # Only 1 result is expected
    except: # WARN : any exception caugth
        res = ""

    return res

def is_advertisement(search_result):
    ''' Return True is the search result is an add '''

    if search_result.find('span', attrs={"class":u"yloca-tip"}):
        return True
    return False

def r_sleep():
    ''' generates a random sleep between 2.000 and MAX_SLEEP seconds '''

    length = float(randint(2000, MAX_SLEEP)) / 1000
    mylog("Safety Random Sleep has started for {0} sec".format(length))
    sleep(length)
    mylog("Safety Random Sleep is over")

def write_query():
    ''' Creates a summary of the query '''

    res = ""
    if CITY:
        res += "City: {0} - ".format(CITY)
    if PARIS_DISTRICTS:
        res += "Paris districts: {0} - ".format(';'.join(PARIS_DISTRICTS))
    res += "Cflts: {0}".format(';'.join(CFLTS))

    return res

# -----------------------------------------------------------------------------
# ---------------------------------- SCRIPT -----------------------------------
# -----------------------------------------------------------------------------

mylog("Script has started")

shops = [] # Init shops list

for cflt in CFLTS: # Check every cflt chosen in the config file
    cur_page = 0 # We are 'placed before' the first page
    while True: # Infinite loop will exit as soon as there is no more shops
        cur_page += 1

        # -- URL OPENING/ HTML PARSING
        cur_url = build_yelp_url(page=cur_page, c=cflt)
        mylog("Start scraping page {0} at {1}".format(cur_page, cur_url))

        # Process the URL with a fake header
        fake_headers = {
            # Headers taken from Chrome spy mode
            'Connection': 'keep-alive',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36',
            'Accept-Encoding': 'gzip, deflate, sdch',
            'Accept-Language': 'fr,en-US;q=0.8,en;q=0.6'}

        r = requests.get(cur_url, headers=fake_headers)
        soup = BeautifulSoup(r.text)

        # -- CLEANING AND PYTHON SHOP OBJECT FILLING
        cpt = 0 # Count init
        # Each shop is in a 'search-result' div
        for sr in soup.find_all('div', attrs={"class":u"search-result"}):

            # If the search result is an advertisement, go to the next one
            if is_advertisement(sr): # Won't allow ads
                continue

            try: # Try to parse desired informations per shop
                cpt += 1
                ext_name = sr.find('a', attrs={"class":u"biz-name"}) \
                           .get_text().strip()
                ext_address = sr.find('address').get_text().strip()
                ext_phone = sr.find('span', attrs={"class":u"biz-phone"}) \
                            .get_text().strip()
                ext_url = sr.find('a', attrs={"class":u"biz-name"})['href']
                ext_district = sr.find(
                    'span',
                    attrs={"class":u"neighborhood-str-list"}).get_text().strip()
                ext_categories = [e.get_text().strip() for e in sr.find(
                    'span', attrs={"class":u"category-str-list"}).find_all('a')]
            except: # If parsing does not work for any reason
                mylog("A shop has been ignored because of parsing error")
                continue

            # Creates a YelpShop only if does not exist, using URL as uniq ID
            if not ext_url in [s.url for s in shops]: # Won't allow duplicates
                shops.append(YelpShop(
                    name=ext_name,
                    address=ext_address,
                    zipcode=extract_zipcode(ext_address),
                    district=ext_district,
                    phone=ext_phone,
                    url=ext_url,
                    categories=ext_categories))

            mylog("New shop created: {0}".format(ext_name))

        if cpt == 0: # There is no more shops to aspire, time to exit
            break

        mylog("Finish scraping page {0} ({1} shops aspirated)".format(cur_page,
                                                                      cpt))

        # Time to sleep for safety
        r_sleep()

mylog("Scraping finished")

# -- XLSX EXPORT
mylog("Start XLSX export, there is {0} shops to write".format(len(shops)))

# Init workbook/worksheet
now = datetime.now()
filename = "yelpscrap-{date}.xlsx".format(date=str(now))
workbook = xlsxwriter.Workbook(filename)
worksheet = workbook.add_worksheet()

# Write Metadata

# -- Query
row = 0
col = 0
worksheet.write(row, col, write_query())

# -- Headers
row = 1
col = 0
heads = ("Shop name", "Address", "ZipCode", "District", "Phone", "Categories")
for head in heads:
    worksheet.write(row, col, head)
    col += 1

# Write Data
row = 2
col = 0
url_format = url_format = workbook.add_format({'font_color': 'blue',
                                               'underline':  1}) # for URLs
for shop in shops:
    worksheet.write_url(row, col, "http://www.yelp.fr{0}".format(shop.url),
                        url_format, shop.name)
    worksheet.write(row, col+1, shop.address)
    worksheet.write(row, col+2, shop.zipcode)
    worksheet.write(row, col+3, shop.district)
    worksheet.write(row, col+4, shop.phone)
    worksheet.write(row, col+5, ';'.join(shop.categories)) # Clean display
    row += 1

workbook.close()
mylog("Finish XLSX export at {0}".format(filename))
