from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from fake_useragent import UserAgent
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.common.by import By
from selenium.common import exceptions as sce
from selenium.webdriver.chrome.options import Options
import time
from pymongo import MongoClient
import os

# Setup working directory to script's location
os.chdir('/Volumes/GitHub/the-average-data-scientist/web-scraping/glassdoor_scrape')


def start_search_session(c_path, c_options, dcap, sargs, tries=20):
    """
    This function tries to open the glassdoor search window. If it detects login page, it will
    then close the chrome session and opens another one to try the luck. After a number of
    tries, it either returns the correctly opened search window or return a NoneType as a
    deciding factor for later operations.
    :param c_path: Path to chromedriver
    :param c_options: Chrome options variable
    :param dcap: Chrome driver's desired_capabilities
    :param sargs: Chrome driver's service arguments
    :param tries: How many times should the function try to obtain the search page
    :return: A correctly opened search window or NoneType
    """
    for i in range(1, tries + 1):
        # Create Chrome webdriver session
        chrome_session = webdriver.Chrome(c_path, chrome_options=c_options,
                                          desired_capabilities=dcap,
                                          service_args=sargs)
        # Get search page
        chrome_session.get('https://www.glassdoor.com/sitedirectory/title-jobs.htm')
        try:  # Detect bad page
            chrome_session.find_element_by_css_selector(
                '.lockedSignUp.d-flex.align-items-center.justify-content-center.flex-column.center')
        except sce.NoSuchElementException:  # Return chrome session if bad page sign NOT found
            return chrome_session
        else:  # Close bad search window and try again if bad page detected
            print("Bad page x{}. Try again".format(i))
            chrome_session.quit()
            continue
    # Return NoneType if all tries failed
    print('Cannot load search page.')
    return None


# Configure Chrome driver
ua = UserAgent()
dcap = dict(DesiredCapabilities.PHANTOMJS)
dcap["phantomjs.page.settings.userAgent"] = ua.random
service_args = ['--ssl-protocol=any', '--ignore-ssl-errors=true']
options = Options()
options.add_argument("--disable-notifications")
options.add_argument("--incognito")
chrome_path = 'chromedriver'

states_list = open('temp_states_list.txt', 'r')
jobs_list = open('job_titles.txt', 'r')

states = states_list.read().split('\n')
jobs = jobs_list.read().split('\n')

states_list.close()
jobs_list.close()


def db_connect():
    with open('db.credential', 'r', encoding='utf-8') as fhand:
        uri, db, col = fhand.read().strip().split('\n')
        return MongoClient(uri)[db][col]

# collection = db_connect()

# Get url list from db
global_urls = list(i['URL'] for i in db_connect().find({}, {"URL": 1, "_id": 0}) if len(i) > 0)
# global_urls = []
new_urls = []

# l = open('logfile.txt', 'a')
# l.write('DateTime' + '|' + 'State' + '|' + 'SearchLoad' + '|' + 'Jobs_Found' + '\n')
# l.close()
# l = open('logfile.txt', 'a')


base_scrape = []
srno = 0

# Search page load detection
driver = start_search_session(c_path=chrome_path, c_options=options, dcap=dcap,
                              sargs=service_args)
if driver:
    print('Good search page obtained')
elif not driver:
    print('Bad search page. Try again after some time')
# time.sleep(3)

for jobtitle in jobs:
    for s in states:

        # l.write(time.strftime("%Y-%m-%d %H:%M:%S") + '|' + s + '|')

        # look for the keyword input box
        jt = driver.find_element_by_xpath("//input[@id = 'sc.keyword']")
        jt.clear()
        jt.send_keys(jobtitle)

        # look for the location input box
        jl = driver.find_element_by_xpath("//input[@id = 'sc.location']")
        jl.clear()
        jl.send_keys(s)

        # click on the search button
        searchbutton = driver.find_element_by_xpath("//button[@id = 'HeroSearchButton']")
        searchbutton.click()
        # l.write('Success' + '|')
        time.sleep(2)

        try:
            jobs_count = driver.find_element_by_xpath("//div[@id = 'MainColSummary']/p")
            jobs = int(jobs_count.text.replace(' Jobs', '').replace(',', ''))
            # l.write(str(jobs) + '\n')
        except:
            # l.write('0' + '\n')
            jobs = 0

        if jobs == 0:
            pages = 0
        else:
            pages = 30

        for p in range(pages):

            jl = driver.find_elements_by_class_name('jl')
            counter = 1
            for job in jl:
                base_dict = {"Source": 'Glassdoor'}

                # Capture the URL of the job posting
                try:
                    url_element = job.find_element_by_class_name('jobLink')
                    url = url_element.get_attribute('href')
                except:
                    continue

                # Check if the job posting already exists in the DB or previous run
                if not url in global_urls and not url in new_urls:

                    # add URL and JobListingID to the DB
                    base_dict['URL'] = url
                    base_dict['JobListingId'] = url.split('jobListingId=', 1)[1]

                    # Designation
                    try:
                        designation = job.find_elements_by_class_name('jobLink')
                        base_dict['Designation'] = designation[1].text
                    except:
                        pass

                    # Company
                    try:
                        company = job.find_elements_by_xpath("//div[@class='flexbox empLoc']/div[1]")
                        base_dict['Company'] = company[counter - 1].text
                    except:
                        pass

                    # Location
                    try:
                        loc = job.find_elements_by_xpath("//div/span[@class='subtle loc']")
                        base_dict['Location'] = loc[counter - 1].text
                    except:
                        pass

                    # Days ago
                    try:
                        days_ago = job.find_elements_by_xpath("//span[@class='minor']")
                        base_dict['Time_posted'] = days_ago[counter - 1].text
                    except:
                        pass

                    '''
                    #New Listing - not relevant at this point
                    try:
                        new_listing = job.find_elements_by_class_name('hotListing')
                        base_dict['NewListing_flag'] = new_listing[0].text
                    except:
                        pass
                    '''
                    # Salary Estimate
                    try:
                        salary_est = job.find_elements_by_xpath('//span[@class="green small"]')
                        base_dict['Salary_est'] = salary_est[counter - 1].text
                    except:
                        pass

                    base_dict['Source'] = "Glassdoor"
                    base_dict['Time_Captured'] = time.strftime("%Y-%m-%d")
                    counter = counter + 1
                    base_scrape.append(base_dict)
                    new_urls.append(url)

                else:
                    # If job posting already exists then go to the next one on the page
                    counter = counter + 1
                    continue

            print(s + ' : Page ' + str(p + 1) + ' done')

            if p != 29:
                nextbutton = driver.find_elements_by_xpath(
                    "//div[@class='pagingControls cell middle']/ul/li[@class = 'next']/a")
                try:
                    # Clicking on the "Next" button if it exists
                    nextbutton[0].click()
                    time.sleep(2)
                    # Closing the popup if it pop ups
                    XBtn = driver.find_elements_by_class_name('xBtn')
                    if len(XBtn) > 0:
                        XBtn[0].click()
                    else:
                        pass
                except:
                    # Going through the next iteration of state as end of pages is reached
                    break

# global_urls.append(new_urls)

# l.close()
# Close current chrome session after each search combination finishes
driver.close()

### Filter out "Indeed Prime" from the company field


######
# - add global list
# - create dicts

