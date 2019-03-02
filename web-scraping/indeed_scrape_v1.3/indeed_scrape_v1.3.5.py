import os
import time
from selenium import webdriver
from selenium.common import exceptions as sce
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from pymongo import errors as pme
from pymongo import MongoClient


def db_connect():
    with open('db.credential', 'r', encoding='utf-8') as fhand:
        return MongoClient(fhand.read().strip()).tads01.Test


def close_popup(chrome_driver):
    """
    This function will detect if there's popup window on the job listing page and will close the
    window if it exist.
    :param chrome_driver: An opened chrome driver session
    :return:
    """
    try:
        pop_window = chrome_driver.find_element_by_css_selector(
            ".popover.popover-foreground.jobalert-popover")
        x_icon = chrome_driver.find_element_by_class_name("popover-x")
    except sce.NoSuchElementException:
        pop_window, x_icon = None, None
    if pop_window:
        try:
            ActionChains(chrome_driver).move_to_element(pop_window).click(x_icon).perform()
        except sce.ElementNotVisibleException:
            print('-------- ! --------')
    return


def load_page(chrome_driver, current_url, tries=4):
    """
    This function is used to ensure the current job listing page is correctly loaded so that
    the scraping can be successfully executed later on.
    :param chrome_driver: An opened chrome driver session
    :param current_url: Current url for the page that's opened
    :param tries: Number of times should the script tries to reload the page when page error detected
    :return: A web element from the loaded page used as a page load response
    """
    close_popup(chrome_driver)
    try:
        # Detect the opened page is loaded correctly or not
        page_response = chrome_driver.find_element_by_id('searchCount').text
    except sce.NoSuchElementException:
        page_response = None
        print('Bad page, try again')
        # Try to load the page another t times
        for t in range(1, tries+1):
            chrome_driver.get(current_url)
            close_popup(chrome_driver)
            try:
                page_response = chrome_driver.find_element_by_id('searchCount').text
                break
            except sce.NoSuchElementException:
                page_response = None
                if t != tries:
                    print('Bad page, try again')
                elif t == tries:
                    break
    return page_response


def find_next_b(chrome_driver):
    """
    This function takes in an opened webdriver session and tries to find the 'next' button on
    the job listing page. It will then click on the button if it exists on the page.
    :param chrome_driver: Opened chrome driver session
    :return: The 'next' button web element (or None if not exist)
    """
    next_b = chrome_driver.find_elements_by_class_name("np")
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


def tp_update():
    # Connect to db
    collection = db_connect()
    # Initiate update counter
    update_counter = 0
    # Calculate and update Time_posted
    for entry in tuple(i for i in collection.find({}, {"Time_captured": 1, "Time_posted": 1, "_id": 1}) if len(i) == 3):
        raw_tp = entry['Time_posted'].strip().lower()
        # Calculate Time_updated
        # 30+ days ago
        if '30+ days ago' in raw_tp:
            calculated_time_posted = None
            collection.update_one({'_id': entry['_id']}, {"$unset": {"Time_posted": ""}})
            update_counter += 1
        # n day(s) ago
        elif ' days ago' in raw_tp or ' day ago' in raw_tp:
            calculated_time_posted = time.strftime("%Y-%m-%d", time.localtime(time.time() - int(raw_tp[:-8]) * 86400))
        # n hour(s) ago
        elif ' hours ago' in raw_tp or ' hour ago' in raw_tp:
            calculated_time_posted = time.strftime("%Y-%m-%d", time.localtime(time.time() - int(raw_tp[:-9]) * 3600))
        # n months ago
        elif ' months ago' in raw_tp:
            calculated_time_posted = time.strftime("%Y-%m-%d",
                                                   time.localtime(time.time() - int(raw_tp[:-10]) * 2592000))
        # other cases (already updated or other unexpected values)
        else:
            calculated_time_posted = None
        # print(calculated_time_posted)
        # Update db entry
        if calculated_time_posted:
            collection.update_one({'_id': entry['_id']}, {"$set": {"Time_posted": calculated_time_posted}},
                                  upsert=False)
            update_counter += 1
        continue
    return update_counter


def scrape_basic_1(chrome_driver, out, existing_urls):
    """
    This function calls close_popup(), load_page(), and find_next_b() functions, takes in an
    opened webdriver session with an indeed job listing page loaded, and go through all of the
    non-sponsored jobs on the page and capture all basic information of those jobs, including
    title, location, detail page link, and capture timestamp.
    :param chrome_driver: Opened chrome driver session
    :param out:
    :param existing_urls:
    :return: A list containing multiple lists with each job's basic info
    """
    # Step 1: find all LEGIT jobs on current page
    jobs = []
    for x in chrome_driver.find_elements_by_css_selector(".row.result.clickcard"):
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
        page = load_page(chrome_driver, current_url=current_url, tries=9)
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
                        chrome_driver.execute_script("window.scrollTo(0, 100000)")
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
        # Update time captured
        job_dict['Time_captured'] = time.time()
        # Find designation
        try:
            job_dict['Designation'] = info.find_element_by_class_name('jobsearch-JobInfoHeader-title')\
                .text.replace('\t', ' ').replace('\n', ' ').strip()
        except sce.NoSuchElementException:
            print('Cannot find job designation detail')
        # Find company name
        try:
            job_dict['Company'] = info.find_element_by_css_selector('.icl-u-lg-mr--sm.icl-u-xs-mr--xs')\
                .text.replace('\t', ' ').replace('\n', ' ').strip()
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
                .text.strip()
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
            stat_s = i.strip().lower().replace('\t', '').replace('\n', '')
            if '30+ days ago' in stat_s or ' days ago' in stat_s or '1 day ago' in stat_s \
                    or ' hours ago' in stat_s or '1 hour ago' in stat_s or ' months ago' in stat_s \
                    or ' month ago' in stat_s:
                job_dict['Time_posted'] = stat_s
                print(stat_s, end=' ')
                break
        try:
            job_dict['Time_posted']
        except KeyError:
            print('Cannot find job posting time', end=' ')
        return
    elif not info:  # Skip page if content is bad
        print('Bad page, moving on...', end=' ')
        return None


def exec_scrape(q_titles, q_states, pts=101):
    """

    :param q_titles: Imported job title list for querying
    :param q_states: Imported state list for querying
    :param pts: How many pages to go through for each combination
    :return: Basic output as a list
    """
    # Configure ChromeDriver (headless)
    c_options = Options()
    c_options.add_argument('--headless')
    c_options.add_argument('--disable-gpu')
    c_path = '{}/chromedriver'.format(os.getcwd())
    # Connect to database
    collection = db_connect()
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
            # break
        # break
    # Initiate insert counter
    insert_counter = 0
    # Scrape detail information & upload each entry to db
    for job in fnl_out:
        scrape_detail_1(chrome, job)
        # Show progress
        print('(#{}/{})'.format(fnl_out.index(job)+1, len(fnl_out)))
        # Insert basic data to db
        try:
            collection.insert_one(job)
        except pme.AutoReconnect:  # Handle db connection error
            while True:
                # Show status
                print('AutoReconnect error. Reconnect to db')
                # Back off 2 seconds
                time.sleep(2)
                # Reconnect to db
                collection = db_connect()
                try:  # Retry insert current job data
                    collection.insert_one(job)
                except pme.AutoReconnect:  # Enter next loop if error occurs again
                    continue
                else:  # Break the loop if data is successfully inserted
                    break
        insert_counter += 1
        continue
    # Scrape complete, quit chrome
    chrome.quit()
    # Print total run time
    print('\r\nRun time: {} seconds\r\n'.format(int(time.time()-start_time)))
    # Show the number of documents inserted into the database
    print('{} new job(s) inserted.\r\n'.format(insert_counter))
    # Calculate & update Time_posted and show update counter
    print('{} Tp field(s) updated.\r\n'.format(tp_update()))
    return


# Setup working directory to script's location
os.chdir(os.path.dirname(os.path.realpath(__file__)))

# Read query inputs from files
with open('q_jobtitles.txt', 'r', encoding='utf-8') as fh:
    qt = list(i.replace(' ', '+') for i in fh.read().strip().split('\n'))
with open('q_states.txt', 'r', encoding='utf-8') as fh:
    qs = list(i for i in fh.read().strip().split('\n') if not i.startswith('#'))

# Execute scrape
exec_scrape(q_titles=qt, q_states=qs, pts=101)
