#get links from the list 
#use the db to pull the url list first and then tie it with first scrape


from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from fake_useragent import UserAgent
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import math


#make browser
ua=UserAgent()
dcap = dict(DesiredCapabilities.PHANTOMJS)
dcap["phantomjs.page.settings.userAgent"] = (ua.random)
service_args=['--ssl-protocol=any','--ignore-ssl-errors=true']
options = Options()
options.add_argument("--disable-notifications")
driver = webdriver.Chrome('chromedriver',desired_capabilities=dcap,service_args=service_args,chrome_options=options)
