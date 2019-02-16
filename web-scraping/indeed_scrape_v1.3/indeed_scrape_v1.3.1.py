import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Setup working directory to script's location
os.chdir(os.path.dirname(os.path.realpath(__file__)))
# print(os.getcwd())


# Define the 'scrape_basic' function to scrape jobs of one designation from one state at a time
def scrape_basic(chrome_driver, q_title, q_state, pages):
    """Take in a opened chromedriver window, a single query job title,
    a single query state name, and a page number to go through the 100 pages
    of the search and return a list of lists in which contain the basic
    information of each job from those 100 pages."""
    print('\n' + q_title, q_state)
    # Initialize Output List
    output = []
    # Initialize search url
    search_url = 'https://www.indeed.com/jobs?q={}&l={}&sort=date'.format(
        q_title, q_state
    )
    # Open up 1st search page
    chrome_driver.get(search_url)
    # Loop the scrape 100 times
    for i in range(pages):
        # pop window detection #
        try:
            pop_window = chrome_driver.find_element_by_css_selector(
                ".popover.popover-foreground.jobalert-popover")
        except:
            pop_window = None
        if pop_window:
            x_icon = chrome_driver.find_element_by_class_name("popover-x")
            x_icon.click()
        # print current page number #
        try:
            print(chrome_driver.find_element_by_id('searchCount').text)
        except:
            print('Bad page. Scrape stopped.')
            time.sleep(5)
            exit()
        # find all LEGIT jobs on current page #
        jobs = []
        for x in chrome_driver.find_elements_by_css_selector(".row.result.clickcard"):
            try:
                sponsored = x.find_element_by_class_name(" sponsoredGray ")
            except:
                sponsored = None
            if sponsored:
                continue
            else:
                jobs.append(x)
            continue
        # extract useful information from each listing #
        for job in jobs:
            # find designation title and page link & clean them up
            try:  # designation type 1
                designation1 = job.find_element_by_css_selector(".jobtitle.turnstileLink") \
                    .text.replace('\t', ' ').replace('\n', ' ').strip()
                page_link = job.find_element_by_css_selector(".jobtitle.turnstileLink") \
                    .get_attribute("href")
            except:  # designation type 2
                try:
                    designation1 = job.find_element_by_class_name("turnstileLink") \
                        .text.replace('\t', ' ').replace('\n', ' ').strip()
                    page_link = job.find_element_by_class_name("turnstileLink") \
                        .get_attribute("href")
                except:  # if designation not found
                    designation1 = 'NA'
                    page_link = 'NA'
            # find company name & clean it up
            try:
                comp_name = job.find_element_by_class_name("company").text.replace('\t', ' ') \
                    .replace('\n', ' ').strip()
            except:
                comp_name = 'NA'
            # find location & clean it up
            location = job.find_element_by_class_name("location").text.replace('\t', ' ') \
                .replace('\n', ' ').strip()
            # gather all information
            output.append([0, designation1, comp_name, location, page_link,
                           time.strftime("%Y-%m-%d")])
            continue
        # find and press "Next" button #
        if not pages == 1:
            chrome_driver.execute_script("window.scrollTo(0, 100000)")
            next_b = chrome_driver.find_elements_by_class_name("np")
            try:
                if len(next_b) == 2:
                    next_b = next_b[1]
                else:
                    next_b = next_b[0]
                    if next_b.text == "« Previous":
                        break
                next_b.click()
            except IndexError:
                print('No more page. Moving on')
                break
        # time.sleep(1)
        continue
    return output


# Define the 'exec_scrape_basic' function to execute the 'scrape_basic'
def exec_scrape_basic(c_path, c_options, q_titles, q_states, pages=100):
    """Take in chromedriver's location, chrome options, query titles and
    states, loop through all of the combinations of job titles and states'
    100 pages. Return a single list of lists of job info for each job
    from the listings."""
    output = []
    chrome = webdriver.Chrome(c_path, chrome_options=c_options)
    for q_title in q_titles:
        for q_state in q_states:
            output += scrape_basic(chrome, q_title, q_state, pages)
    chrome.quit()
    return output


# Read search inputs from files
with open('q_jobtitles.txt', 'r', encoding='utf-8') as fh:
    qt = list(i.replace(' ', '+') for i in fh.read().split('\n'))
with open('q_states.txt', 'r', encoding='utf-8') as fh:
    qs = fh.read().split()

# Setup ChromeDriver (headless)
chrome_path = '/usr/bin/chromedriver'
options = Options()
options.add_argument('--headless')
options.add_argument('--disable-gpu')

# Execute basic scrape
b_out = exec_scrape_basic(chrome_path, options, qt, qs, pages=1)
