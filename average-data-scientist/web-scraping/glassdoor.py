
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from fake_useragent import UserAgent
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time


#make browser
ua=UserAgent()
dcap = dict(DesiredCapabilities.PHANTOMJS)
dcap["phantomjs.page.settings.userAgent"] = (ua.random)
service_args=['--ssl-protocol=any','--ignore-ssl-errors=true']
options = Options()
options.add_argument("--disable-notifications")
driver = webdriver.Chrome('chromedriver',desired_capabilities=dcap,service_args=service_args,chrome_options=options)


#f = open('glassdoor.txt', 'a')
#f.write('Date' + '|' + 'Sr_No' + '|' + 'Designation' + '|' + 'Company' + '|' + 'Location' + '|' + 'Days_Ago' + '|' + 'New_Listing' + '|' + 'Salary_Estimate' + '|' + 'URL' + '\n')
#f.close()
f = open('glassdoor.txt', 'a')


srno = 0

for pagenum in range(1,101):
    
    if pagenum == 1:
        #Opening the first page
        driver.get('https://www.glassdoor.com/Job/data-scientist-jobs-SRCH_KO0,14.htm')
        time.sleep(5)
    else:
        #Clicking on the "Next" button
        nextbutton = driver.find_elements_by_xpath("//div[@class='pagingControls cell middle']/ul/li[@class = 'next']/a")
        nextbutton[0].click()
    
    #Closing the popup
    XBtn = driver.find_elements_by_class_name('xBtn')
    if len(XBtn) > 0:
        XBtn[0].click()
    else:
        pass
      
    jl = driver.find_elements_by_class_name('jl')
    counter = 1
    for job in jl:
        srno = (pagenum-1)*30 + counter
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
            
        #Job URL
        try:
            url = job.find_element_by_class_name('jobLink')
            f.write(url.get_attribute('href'))
        except:
            f.write('Not Found')
            
        f.write('\n')
        counter = counter + 1
    
    print("Page " + str(pagenum) + " done")


f.close()
driver.close()




### Filter out "Indeed Prime" from the company field

########################################





driver.get('https://www.glassdoor.com/index.htm')
time.sleep(5)

jt = driver.find_element_by_xpath("//input[@id = 'KeywordSearch']")
jt.clear()
jt.send_keys('Data Scientist')

jl = driver.find_element_by_xpath("//input[@id = 'LocationSearch']")
jl.clear()
jl.send_keys('AZ')

searchbutton = driver.find_element_by_xpath("//button[@id = 'HeroSearchButton']")
searchbutton.click()



