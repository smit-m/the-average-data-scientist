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
options.add_argument("--incognito")
driver = webdriver.Chrome('chromedriver',desired_capabilities=dcap,service_args=service_args,chrome_options=options)


states_list = open('temp_states_list.txt', 'r')
jobs_list = open('job_titles.txt', 'r')


states = states_list.read().split('\n')
jobs = jobs_list.read().split('\n')

states_list.close()
jobs_list.close()



#l = open('logfile.txt', 'a')
#l.write('DateTime' + '|' + 'State' + '|' + 'SearchLoad' + '|' + 'Jobs_Found' + '\n')
#l.close()
l = open('logfile.txt', 'a')

#f = open('glassdoor.txt', 'a')
#f.write('Date' + '|' + 'Sr_No' + '|' + 'Designation' + '|' + 'Company' + '|' + 'Location' + '|' + 'Days_Ago' + '|' + 'New_Listing' + '|' + 'Salary_Estimate' + '|' + 'URL' + '|' + 'JobListingID' + '\n')
#f.close()
f = open('glassdoor.txt', 'a')

global_jobURLs = []
srno = 0
for jobtitle in jobs:
    for s in states:
        l.write(time.strftime("%Y-%m-%d %H:%M:%S") + '|' + s + '|')
        driver.get('https://www.glassdoor.com/sitedirectory/title-jobs.htm')
        time.sleep(3)
        
        
        #look for the keyword input box
        jt = driver.find_element_by_xpath("//input[@id = 'sc.keyword']")
        jt.clear()
        jt.send_keys(jobtitle)
        
        #look for the location input box
        jl = driver.find_element_by_xpath("//input[@id = 'sc.location']")
        jl.clear()
        jl.send_keys(s)
        
        #click on the search button
        searchbutton = driver.find_element_by_xpath("//button[@id = 'HeroSearchButton']")
        searchbutton.click()
        l.write('Success' + '|')
        time.sleep(2)
        
        try:
            jobs_count = driver.find_element_by_xpath("//div[@id = 'MainColSummary']/p")
            jobs = int(jobs_count.text.replace(' Jobs', '').replace(',', ''))
            l.write(str(jobs) + '\n')
        except:
            l.write('0' + '\n')
            jobs = 0
            
        if jobs == 0:
            pages = 0
        elif jobs < 901:
            pages = math.ceil(jobs/30)
        else:
            pages = 30
            
        
        for p in range(pages):
            
            time.sleep(2)
            #Closing the popup if it pop ups
            XBtn = driver.find_elements_by_class_name('xBtn')
            if len(XBtn) > 0:
                XBtn[0].click()
            else:
                pass
              
            jl = driver.find_elements_by_class_name('jl')
            counter = 1
            for job in jl:
                srno = p*30 + counter
                f.write(time.strftime("%Y-%m-%d") + '|' + str(srno) + '|')
                
                #Designation
                try:
                    designation = job.find_elements_by_class_name('jobLink')
                    f.write(designation[1].text + '|')
                except:
                    f.write('Not Found' + '|')
                    
                #Company
                try:
                    company = job.find_elements_by_xpath("//div[@class='flexbox empLoc']/div[1]")
                    f.write(company[counter-1].text + '|')
                except:
                    f.write('Not Found' + '|')
                    
                #Location
                try:
                    loc = job.find_elements_by_xpath("//div/span[@class='subtle loc']")
                    f.write(loc[counter-1].text + '|')
                except:
                    f.write('Not Found' + '|')
                
                #Days ago
                try:
                    days_ago = job.find_elements_by_xpath("//span[@class='minor']")
                    f.write(days_ago[counter-1].text + '|')
                except:
                    f.write('Not Found' + '|')
                    
                #New Listing
                try:
                    new_listing = job.find_elements_by_class_name('hotListing')
                    f.write(new_listing[0].text + '|')
                except:
                    f.write('Not Found' + '|')
                    
                #Salary Estimate
                try:
                    salary_est = job.find_elements_by_xpath('//span[@class="green small"]')
                    f.write(salary_est[counter-1].text + '|')
                except:
                    f.write('Not Found' + '|')
                    
                #Job URL and JobListingID
                try:
                    url = job.find_element_by_class_name('jobLink')
                    f.write(url.get_attribute('href') + '|')
                    f.write(url.get_attribute('href').split('jobListingId=', 1)[1])
                    global_jobURLs.append(url.get_attribute('href'))
                except:
                    f.write('Not Found' + '|')
                    f.write('Not Found')
                    
                f.write('\n')
                counter = counter + 1
                
            print(s + ' : Page ' + str(p+1) + ' done')
            if p == pages-1:
                #Going through the next iteration of state as end of pages is reached
                break
            else:
                #Clicking on the "Next" button
                nextbutton = driver.find_elements_by_xpath("//div[@class='pagingControls cell middle']/ul/li[@class = 'next']/a")
                nextbutton[0].click()
        


global_jobURLs.clear()
f.close()
l.close()
driver.close()


### Filter out "Indeed Prime" from the company field
