import os
import time
from selenium import webdriver
from selenium.common import exceptions as sce
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from datetime import datetime, timedelta
from pymongo import MongoClient

# Setup working directory to script's location
os.chdir(os.path.dirname(os.path.realpath(__file__)))

# Setup ChromeDriver (headless)
options = Options()
options.add_argument('--headless')
options.add_argument('--disable-gpu')
chrome_path = '/usr/bin/chromedriver'


def close_popup(driver):
    """
    This function will detect if there's popup window on the job listing page and will close the
    window if it exist.
    :param driver: An opened chrome driver session
    :return:
    """
    try:
        pop_window = driver.find_element_by_css_selector(
            ".popover.popover-foreground.jobalert-popover")
        x_icon = driver.find_element_by_class_name("popover-x")
    except sce.NoSuchElementException:
        pop_window, x_icon = None, None
    if pop_window:
        try:
            ActionChains(driver).move_to_element(pop_window).click(x_icon).perform()
        except sce.ElementNotVisibleException:
            print('-------- ! --------')
    return


def load_page(driver, c_url, tries=4):
    """
    This function is used to ensure the current job listing page is correctly loaded so that
    the scraping can be successfully executed later on.
    :param driver: An opened chrome driver session
    :param c_url: Current url for the page that's opened
    :param tries: Number of times should the script tries to reload the page when page error detected
    :return: A web element from the loaded page used as a page load response
    """
    close_popup(driver=driver)
    try:
        # Detect the opened page is loaded correctly or not
        page_response = driver.find_element_by_id('searchCount').text
    except sce.NoSuchElementException:
        page_response = None
        print('Bad page, try again')
        # Try to load the page another t times
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


def find_next_b(driver):
    """
    This function takes in an opened webdriver session and tries to find the 'next' button on
    the job listing page. It will then click on the button if it exists on the page.
    :param driver: Opened chrome driver session
    :return: The 'next' button web element (or None if not exist)
    """
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


def scrape_basic_1(driver, out, existing_urls):
    """
    This function calls close_popup(), load_page(), and find_next_b() functions, takes in an
    opened webdriver session with an indeed job listing page loaded, and go through all of the
    non-sponsored jobs on the page and capture all basic information of those jobs, including
    title, location, detail page link, and capture timestamp.
    :param driver: Opened chrome driver session
    :param out:
    :param existing_urls:
    :return: A list containing multiple lists with each job's basic info
    """
    # Step 1: find all LEGIT jobs on current page
    jobs = []
    for x in driver.find_elements_by_css_selector(".row.result.clickcard"):
        try:
            x.find_element_by_class_name(" sponsoredGray ")
        except sce.NoSuchElementException:
            jobs.append(x)
        continue
    # Step 2: extract information from each job
    for job in jobs:
        # 2.1 Initiate job_out dictionary for storing data
        job_out = dict()
        # 2.2: find designation title and page link
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
                designation1 = None
                page_link = None
        if designation1 and page_link:  # Add data if captured
            if page_link in existing_urls:  # Check for duplicate
                continue
            elif page_link not in existing_urls:
                job_out['Designation'], job_out['URL'] = designation1, page_link
                existing_urls.add(page_link)
        else:  # Skip if designation or page_link not found
            continue
        # 2.3: find company name
        try:
            comp_name = job.find_element_by_class_name("company").text.replace('\t', ' ') \
                .replace('\n', ' ').strip()
        except sce.NoSuchElementException:
            print('Company name not found')
        else:
            job_out['Company'] = comp_name
        # 2.4: find location
        try:
            location = job.find_element_by_class_name("location").text.replace('\t', ' ')\
                .replace('\n', ' ').strip()
        except sce.NoSuchElementException:
            print('Location not found')
        else:
            job_out['Location'] = location
        # 2.5: add capture timestamp
        job_out['Time_captured'] = time.time()
        # 2.6: add source
        job_out['Source'] = 'Indeed'
        # 2.7: gather all information and append to output list
        out.append(job_out)
    return


def scrape_basic_100(chrome_driver, q_title, q_state, out, existing_urls, pages_to_search):
    """
    This function calls b_scrape_current_page() function and takes in parameters to scrape
    through 100 (or less) job listing pages from the generated search url.
    :param chrome_driver: Opened chrome driver session
    :param q_title: One query job title
    :param q_state: One query state name
    :param out:
    :param existing_urls:
    :param pages_to_search: Desired page number for the function to scrape through
    :return:
    """
    # Show current query combination
    print('\n' + q_title.replace('+', ' '), q_state)
    # Generate search url
    search_url = 'https://www.indeed.com/jobs?q={}&l={}&sort=date'.format(
        q_title, q_state)
    # Open up 1st search page
    chrome_driver.get(search_url)
    # Scrape 100 (or less) pages
    for i in range(pages_to_search):
        # Get current page's url
        current_url = chrome_driver.current_url
        # Get page load response or try to reload
        page = load_page(chrome_driver, current_url, tries=9)
        # Scrape or break
        if page:  # if successfully loaded
            # print current page number and page url
            print('{} | {}'.format(page, current_url))
            # scrape current page
            scrape_basic_1(chrome_driver,
                           out=out,
                           existing_urls=existing_urls)
            # find and press "next" button
            if not pages_to_search == 1:
                next_b = find_next_b(chrome_driver)
                if next_b:
                    try:
                        next_b.click()
                    except sce.WebDriverException:
                        print('\r\nNEXT BUTTON NOT CLICKABLE, MOVING ON...\r\n')
                        break
                elif not next_b:
                    break
            # optional sleep
            time.sleep(0)
        elif not page:  # if current page won't load
            # end the entire scrape loop
            print('Bad page, moving on...')
            break
        continue
    return


def scrape_detail_1(chrome_driver, job_dict, tries=3):
    """

    :param chrome_driver:
    :param job_dict:
    :param tries:
    :return:
    """
    # Show URL
    print('\r\nDetail page: ' + job_dict['URL'])
    # Content check
    info = None
    for t in range(tries):
        chrome_driver.get(job_dict['URL'])
        try:
            info = chrome_driver.find_element_by_class_name('jobsearch-JobComponent')
        except sce.NoSuchElementException:  # Bad luck, try open the link again
            print('Bad luck x{}'.format(t+1))
            time.sleep(1)
        else:
            break
    if info:  # Enter scraping stage if content checks out
        # Find designation
        try:
            job_dict['Designation'] = info.find_element_by_class_name('jobsearch-JobInfoHeader-title')\
                .text.replace('\t', '').replace('\n', '').strip()
        except sce.NoSuchElementException:
            print('Cannot find job designation detail')
        # Find company name
        try:
            job_dict['Company'] = info.find_element_by_css_selector('.icl-u-lg-mr--sm.icl-u-xs-mr--xs')\
                .text.replace('\t', '').replace('\n', '').strip()
        except sce.NoSuchElementException:
            print('Cannot find company name detail')
        # Find location
        try:
            job_dict['Location'] = info.find_element_by_class_name('jobsearch-InlineCompanyRating')\
                .text.split('-')[-1].replace('\t', ' ').replace('\n', ' ').strip()
        except sce.NoSuchElementException:
            print('Cannot find job location detail')
        # Find job description
        try:
            job_dict['Description'] = info.find_element_by_class_name('jobsearch-JobComponent-description')\
                .text.replace('\t', ' ').replace('\n', ' ').strip()
        except sce.NoSuchElementException:
            print('Cannot find job description detail')
        # Find original job's page link
        try:
            job_dict['Origin_URL'] = info.find_element_by_xpath('//*[@id="originalJobLinkContainer"]/a')\
                .get_attribute("href")
        except sce.NoSuchElementException:
            print("Cannot find job's original page link")
        # Find and calculate time posted
        for i in info.find_element_by_class_name('jobsearch-JobMetadataFooter').text.split('-'):
            item = i.strip().lower()
            if 'hour' in item or 'day' in item or 'minute' in item or 'now' in item:
                stat_s = item.strip().replace('\t', '').replace('\n', '')
                print(stat_s, end=' ')
                if '30+ days ago' in stat_s:
                    job_dict['Time_posted'] = str('Too old')
                    break
                elif ' days ago' in stat_s:
                    m_day = int(stat_s[:-9])
                    job_dict['Time_posted'] = str(datetime.strftime(datetime.now() - timedelta(m_day), '%Y-%m-%d'))
                    break
                elif '1 day ago' in stat_s:
                    job_dict['Time_posted'] = str(datetime.strftime(datetime.now() - timedelta(1), '%Y-%m-%d'))
                    break
                elif ' hour' in stat_s:
                    if int(time.strftime('%H')) - int(stat_s[:-9].strip()) > 0:
                        job_dict['Time_posted'] = str(datetime.strftime(datetime.now(), '%Y-%m-%d'))
                        break
                    else:
                        job_dict['Time_posted'] = str(datetime.strftime(datetime.now() - timedelta(1), '%Y-%m-%d'))
                        break
                else:
                    job_dict['Time_posted'] = stat_s
                    break
        return
    elif not info:  # Skip page if content is bad
        print('Bad page, moving on...', end=' ')
        return None


def exec_scrape(c_path, c_options, q_titles, q_states, db_cred_file, pts=101):
    """
    This function loops through the required search parameters combinations and then executes
    the scrape_basic() function to scrape basic information for each of the combinations. It
    returns a list containing all the data stored in multiple lists.
    :param c_path: Chrome_driver's location
    :param c_options: Chrome_driver's options
    :param q_titles: Imported job title list for querying
    :param db_cred_file:
    :param q_states: Imported state list for querying
    :param pts: How many pages to go through for each combination
    :return: Basic output as a list
    """
    # Connect to database
    with open(db_cred_file, 'r', encoding='utf-8') as fhand:
        collection = MongoClient(fhand.read().strip()).tads01.Test
    # Get url list from db
    e_urls = set(
        i['URL'] for i in collection.find({}, {"URL": 1, "_id": 0})
        if len(i) > 0)
    # Initiate output list
    fnl_out = list()
    # Record start time
    start_time = time.time()
    # Open up a chrome driver session
    chrome = webdriver.Chrome(c_path, chrome_options=c_options)
    # Loop through all query combinations and scrape basic information (Scrape basic)
    for q_title in q_titles:
        for q_state in q_states:
            # Scrape current search combination
            scrape_basic_100(chrome_driver=chrome,
                             q_title=q_title,
                             q_state=q_state,
                             out=fnl_out,
                             existing_urls=e_urls,
                             pages_to_search=pts)
            # Show accumulative total of new jobs obtained after current scrape
            print('(Accumulative total: {})'.format(len(fnl_out)))
    # Scrape detail & update basic_out
    for job in fnl_out:
        scrape_detail_1(chrome, job)
        # Show progress
        print('(#{}/{})'.format(fnl_out.index(job)+1, len(fnl_out)))
    # Scrape complete, quit chrome
    chrome.quit()
    # Print total run time
    print('\r\nRun time: {} seconds\r\n'.format(int(time.time()-start_time)))
    # Initiate insert counter
    insert_counter = 0
    # Insert basic data to db
    for item in fnl_out:
        collection.insert_one(item)
        insert_counter += 1
        continue
    return insert_counter


# Read query input from files
with open('q_jobtitles.txt', 'r', encoding='utf-8') as fh:
    qt = list(i.replace(' ', '+') for i in fh.read().strip().split('\n'))
with open('q_states.txt', 'r', encoding='utf-8') as fh:
    qs = fh.read().strip().split('\n')

# Execute basic scrape
new_job_count = exec_scrape(c_path=chrome_path,
                            c_options=options,
                            q_titles=qt,
                            q_states=qs,
                            db_cred_file='.dbcredential',
                            pts=101)
# Show the number of documents inserted into the database
print('\r\n{} new job(s) inserted.\r\n'.format(new_job_count))
