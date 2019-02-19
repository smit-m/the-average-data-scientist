import os
import time
from selenium import webdriver
from selenium.common import exceptions as sce
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains

# Setup working directory to script's location
os.chdir(os.path.dirname(os.path.realpath(__file__)))

# Setup ChromeDriver (headless)
options = Options()
options.add_argument('--headless')
options.add_argument('--disable-gpu')
chrome_path = '/usr/bin/chromedriver'


# Define the 'close_popup' function to find popup window (if exist) and close it
def close_popup(driver):
    try:
        pop_window = driver.find_element_by_css_selector(
            ".popover.popover-foreground.jobalert-popover")
        x_icon = driver.find_element_by_class_name("popover-x")
    except sce.NoSuchElementException:
        pop_window, x_icon = None, None
    if pop_window:
        try:
            ActionChains(driver).move_to_element(pop_window).click(x_icon).perform()
            # x_icon.click()
        except sce.ElementNotVisibleException:
            print('-------- ! --------')


# The 'load page' function will detect bad page and will behave base on it's finding
def load_page(driver, c_url):
    close_popup(driver=driver)
    try:
        # Detect the opened page is loaded correctly or not
        page_response = driver.find_element_by_id('searchCount').text
    except sce.NoSuchElementException:
        page_response = None
        print('Bad page, try again')
        # Try to load the page another 4 times
        tries = 4
        for t in range(1, tries+1):
            driver.get(c_url)
            close_popup(driver=driver)
            try:
                page_response = driver.find_element_by_id('searchCount').text
                break
            except sce.NoSuchElementException:
                page_response = None
                if t != tries:
                    print('Bad page, try again')
                elif t == tries:
                    break
    return page_response


# Find next button function finds the 'next' button and clicks on it (if exist)
def find_next_b(driver):
    next_b = driver.find_elements_by_class_name("np")
    if len(next_b) == 2:
        next_b = next_b[1]
    elif len(next_b) == 0:
        next_b = None
        print('No more page, moving on...(1)')
    elif len(next_b) == 1:
        next_b = next_b[0]
        if next_b.text == "« Previous":
            next_b = None
            print('No more page, moving on...(0)')
    else:
        next_b = None
        print('No more page, moving on...(2)')
    return next_b


# Define the function to scrape through each listing page
def b_scrape_current_page(driver):
    cp_out = []
    # find all LEGIT jobs on current page
    jobs = []
    for x in driver.find_elements_by_css_selector(".row.result.clickcard"):
        try:
            x.find_element_by_class_name(" sponsoredGray ")
        except sce.NoSuchElementException:
            jobs.append(x)
        continue
    # extract information from each job
    for job in jobs:
        # find designation title and page link & clean them up
        try:  # designation type 1
            designation1 = job.find_element_by_css_selector(".jobtitle.turnstileLink") \
                .text.replace('\t', ' ').replace('\n', ' ').strip()
            page_link = job.find_element_by_css_selector(".jobtitle.turnstileLink") \
                .get_attribute("href")
        except sce.NoSuchElementException:
            try:  # designation type 2
                designation1 = job.find_element_by_class_name("turnstileLink") \
                    .text.replace('\t', ' ').replace('\n', ' ').strip()
                page_link = job.find_element_by_class_name("turnstileLink") \
                    .get_attribute("href")
            except sce.NoSuchElementException:  # designation not found
                designation1 = 'NA'
                page_link = 'NA'
        # find company name & clean it up
        try:
            comp_name = job.find_element_by_class_name("company").text.replace('\t', ' ') \
                .replace('\n', ' ').strip()
        except sce.NoSuchElementException:
            comp_name = 'NA'
        # find location & clean it up
        location = job.find_element_by_class_name("location").text.replace('\t', ' ') \
            .replace('\n', ' ').strip()
        # gather all information
        cp_out.append([time.time(), designation1, comp_name, location, page_link,
                       time.strftime("%Y-%m-%d")])
        continue
    return cp_out


# Define the 'scrape_basic' function to scrape jobs of one designation in one state
def scrape_basic(chrome_driver, q_title, q_state, pages_to_search):
    """Take in a opened chromedriver window, a single query job title,
    a single query state name, and a page number to go through the 100 pages
    of the search and return a list of lists in which contain the basic
    information of each job from those 100 pages."""
    print('\n' + q_title.replace('+', ' '), q_state)
    # Initialize Output List
    cs_out = []
    # Initialize search url
    search_url = 'https://www.indeed.com/jobs?q={}&l={}&sort=date'.format(
        q_title, q_state
    )
    # Open up 1st search page
    chrome_driver.get(search_url)
    # Loop the scrape 100 times
    for i in range(pages_to_search):
        current_url = chrome_driver.current_url
        # get page response/reload
        good_response = load_page(chrome_driver, current_url)
        # end current scrape if page won't load
        if good_response:
            print('{} | {}'.format(good_response, current_url))
        elif not good_response:
            print('Bad page, moving on...')
            break
        # scrape current page
        cs_out += b_scrape_current_page(chrome_driver)
        # Find and press "next" button
        if not pages_to_search == 1:
            next_b = find_next_b(chrome_driver)
            if next_b:
                next_b.click()
            elif not next_b:
                break
        # time.sleep(1)
        continue
    return cs_out


# Define the 'exec_scrape_basic' function to execute the 'scrape_basic'
def exec_scrape_basic(c_path, c_options, q_titles, q_states, pts=101):
    """Take in chromedriver's location, chrome options, query titles and
    states, loop through all of the combinations of job titles and states'
    100 pages. Return a single list of lists of job info for each job
    from the listings."""
    basic_out = []
    chrome = webdriver.Chrome(c_path, chrome_options=c_options)
    for q_title in q_titles:
        for q_state in q_states:
            basic_out += scrape_basic(chrome, q_title, q_state, pts)
    chrome.quit()
    return basic_out


# Read search inputs from files
with open('q_jobtitles.txt', 'r', encoding='utf-8') as fh:
    qt = list(i.replace(' ', '+') for i in fh.read().strip().split('\n'))
with open('q_states.txt', 'r', encoding='utf-8') as fh:
    qs = fh.read().strip().split('\n')

# Execute basic scrape
b_out = exec_scrape_basic(chrome_path, options, qt, qs)
