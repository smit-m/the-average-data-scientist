import os
import sys
import time
from selenium import webdriver
from selenium.common import exceptions as sce
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains

os.chdir('/media/calvin-pc_share/the-average-data-scientist/web-scraping/indeed_scrape_v1.3')


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


def load_page(driver, c_url):
    close_popup(driver=driver)
    try:
        page_response = driver.find_element_by_id('searchCount').text
    except sce.NoSuchElementException:
        page_response = None
        print('Bad page, try again')
        # Try to load the page another n times
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

search_url = 'https://www.indeed.com/jobs?q=Data+Analyst&l=DC&sort=date'
chrome_driver = webdriver.Chrome(chrome_path, chrome_options=options)
chrome_driver.get(search_url)
pages_to_scrape = 101  # 101

for i in range(pages_to_scrape):
    current_url = chrome_driver.current_url
    # get page response/reload
    good_response = load_page(chrome_driver, current_url)
    # end current scrape if page won't load
    if good_response:
        print(good_response)
    elif not good_response:
        print('Bad page, moving on...')
        break
    # find all LEGIT jobs on current page
    jobs = []
    for x in chrome_driver.find_elements_by_css_selector(".row.result.clickcard"):
        try:
            sponsored = x.find_element_by_class_name(" sponsoredGray ")
        except:
            jobs.append(x)
        continue
    print('Found {} job(s)\r\n'.format(len(jobs)))
    # Find and press "next" button #
    if not pages_to_scrape == 1:
        next_b = find_next_b(chrome_driver)
        if next_b:
            next_b.click()
        elif not next_b:
            break

chrome_driver.close()
