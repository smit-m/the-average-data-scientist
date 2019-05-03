import os
import time
from selenium import webdriver
from selenium.common import exceptions as sce
from selenium.webdriver.chrome.options import Options
from pymongo import errors as pme
from pymongo import MongoClient


def read(file):
    # Same function as before (read query inputs)
    with open(file, 'r') as fh:
        return fh.read().strip().split('\n')


def db_connect():
    with open('db.credential', 'r', encoding='utf-8') as fhand:
        uri, db, col = fhand.read().strip().split('\n')
        return MongoClient(uri)[db][col]


def get_existing_urls():
    # Get existing url list from db
    try:
        return list(i['URL'] for i in db_connect().find({}, {"URL": 1, "_id": 0}) if len(i) > 0)
    except pme.ServerSelectionTimeoutError:  # If connection timed out
        print('DB server timed out. Global_urls set to empty')
        return list()
    except ValueError:  # If db cred file content error
        print('Db.credential file content error. Global_urls set to empty')
        return list()


def push_to_db(dict_list):
    try:
        collection = db_connect()
    except:
        print('Bad Connection. Insertion task failed!')
        pass
    else:
        if len(dict_list) > 0:
            insert_counter = 0
            for item in dict_list:
                collection.insert_one(item)
                insert_counter += 1
                continue
            print('{} record(s) inserted'.format(insert_counter))


def obtain_search_page(chrome_driver, tries=5):
    """
    This function tries to open the glassdoor search window. If it detects login page, it will
    then close the chrome session and opens another one to try the luck. After a number of
    tries, it either returns the correctly opened search window or return a NoneType as a
    deciding factor for later operations.
    :param chrome_driver:
    :param tries: How many times should the function try to obtain the search page
    :return: A correctly opened search window or NoneType
    """
    for i in range(1, tries + 1):
        # Get search page
        chrome_driver.get('https://www.glassdoor.com/sitedirectory/title-jobs.htm')
        try:  # Detect bad page
            chrome_driver.find_element_by_css_selector(
                '.lockedSignUp.d-flex.align-items-center.justify-content-center.flex-column.center')
        except sce.NoSuchElementException:  # Return chrome session if bad page sign NOT found
            return True
        else:  # Close bad search window and try again if bad page detected
            print("Bad page x{}. Try again".format(i))
            continue
    # Return NoneType if all tries failed
    print('Cannot load search page.')
    return False


def scrape_one_iter(chrome_driver, g_urls, out_ls, j_title, j_location):
    # Get search page
    if obtain_search_page(chrome_driver):
        # Enter search keywords
        jt = chrome_driver.find_element_by_id("sc.keyword")
        jt.clear()
        jt.send_keys(j_title)

        # Enter location input
        jl = chrome_driver.find_element_by_id("sc.location")
        jl.clear()
        jl.send_keys(j_location)

        # Click on the search button
        searchbutton = chrome_driver.find_element_by_id("HeroSearchButton")
        searchbutton.click()
        print('\r\n{} | {}'.format(j_title, j_location))
        time.sleep(2)

        # Loop through pages (maximum 30 pages)
        for p in range(30):
            for job in chrome_driver.find_elements_by_class_name('jl'):
                base_dict = {"Source": 'Glassdoor'}
                # Job content check up
                try:
                    url = job.find_element_by_class_name('jobLink').get_attribute('href')
                except sce.NoSuchElementException:  # skip iteration if no url
                    continue
                else:  # Scrape on if url found
                    # Check url for duplicates
                    if url in g_urls:  #Skip iteration if url exists in db
                        continue
                    elif url not in g_urls:  # Scrape on if url does not exist

                        # Append url to global_urls list
                        g_urls.append(url)

                        # Add URL and JobListingID to output dict
                        base_dict['URL'] = url
                        base_dict['JobListingId'] = url.split('jobListingId=', 1)[1]
                        # Grab Designation
                        try:
                            base_dict['Designation'] = job.find_elements_by_class_name('jobLink')[1].text
                        except sce.NoSuchElementException:
                            pass
                        # Grab Company Name (DO NOT CHANGE THE .SPLIT()!)
                        try:
                            base_dict['Company'] = \
                            job.find_element_by_css_selector(".flexbox.empLoc").text.split(' – ')[0]
                        except sce.NoSuchElementException:
                            pass
                        # Grab Location
                        try:
                            base_dict['Location'] = job.find_element_by_css_selector(".subtle.loc").text
                        except sce.NoSuchElementException:
                            pass
                        # Grab Days Ago
                        try:
                            base_dict['Time_posted'] = job.find_element_by_css_selector('.minor').text
                        except sce.NoSuchElementException:
                            pass
                        # Grab Salary Estimate
                        try:
                            base_dict['Salary_est'] = job.find_element_by_css_selector('.green.small').text
                        except sce.NoSuchElementException:
                            pass
                        # Add Time Captured to output dictionary
                        base_dict['Time_captured'] = time.strftime("%Y-%m-%d")

                        # Append to final output list or directly write to db
                        out_ls.append(base_dict)
                    else:
                        # If job posting already exists then go to the next one on the page
                        continue

            # Show status
            print('{} : Page {} done'.format(j_location, p + 1))

            # Get ready for next iteration
            if p != 29:
                try:
                    nxtb = chrome_driver.find_element_by_class_name("next")
                except sce.NoSuchElementException:  # Break if 'next' button not found
                    break
                else:  # If 'next' button found
                    try:  # Detect if disabled
                        nxtb.find_element_by_class_name('disabled')
                    except sce.NoSuchElementException:  # If not disabled
                        nxtb.click()
                        time.sleep(2)
                        try:  # Close the popup if exist
                            chrome_driver.find_element_by_class_name('xBtn').click()
                        except sce.NoSuchElementException:
                            pass
                    else:  # Break the loop if nxtb is disabled (last page hit)
                        break
    return


# Set working directory
# os.chdir('/Volumes/GitHub/the-average-data-scientist/web-scraping/glassdoor_scrape')
os.chdir(os.path.dirname(os.path.realpath(__file__)))

# Define variables
locations = read('location_list.txt')
jobs = read('job_titles.txt')
global_urls = get_existing_urls()
chrome_path = os.getcwd() + '/chromedriver'

# Configure Chrome driver
options = Options()
options.add_argument("--disable-notifications")
options.add_argument("--incognito")

# Open Chrome driver
driver = webdriver.Chrome(chrome_path, options=options)

# Scrape for all iterations
for jobtitle in jobs:
    for loc in locations:
        base_scrape = list()
        try:  # Try the general Scrape() function
            scrape_one_iter(chrome_driver=driver, g_urls=global_urls, out_ls=base_scrape, j_title=jobtitle,
                            j_location=loc)
        except:  # If any unexpected error occurred
            print('UNEXPECTED ERROR. Skip to next iteration')
        finally:  # Call push_to_db() no matter what happened
            push_to_db(base_scrape)

# Close current chrome session after each search combination finishes
driver.quit()


### Filter out "Indeed Prime" from the company field - ?
