#get links from the list 
#use the db to pull the url list first and then tie it with first scrape


import os
import time
from selenium import webdriver
from selenium.common import exceptions as sce
from selenium.webdriver.chrome.options import Options
from pymongo import errors as pme
from pymongo import MongoClient


#make browser
ua=UserAgent()
dcap = dict(DesiredCapabilities.PHANTOMJS)
dcap["phantomjs.page.settings.userAgent"] = (ua.random)
service_args=['--ssl-protocol=any','--ignore-ssl-errors=true']
options = Options()
options.add_argument("--disable-notifications")
driver = webdriver.Chrome('chromedriver',desired_capabilities=dcap,service_args=service_args,chrome_options=options)
