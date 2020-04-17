from bs4 import BeautifulSoup
from selenium import webdriver
import datetime
import time

def no_space(text):
    return text.strip()

driver = webdriver.Chrome(r"C:\Users\webiznet\Downloads\chromedriver_win32\chromedriver.exe")
driver.get("https://rinsms.paran.com/spa/account/login.do")
driver.find_element_by_name("j_username").send_keys("ktmedia")
driver.find_element_by_name("j_password").send_keys("zpdlxl1!")
driver.find_element_by_xpath("""//*[@id="loginForm"]/fieldset/p/input""").click()

day_delta = datetime.timedelta(days=-1)
start_date = datetime.date.today()
end_date = start_date + -7 * day_delta

file = open("test1.csv", "w", newline="")

for i in range((end_date - start_date).days):
    date = start_date + i * day_delta
    driver.get("https://rinsms.paran.com/spa/admin/mng/pushmng/timetraffic.ajax?searchDt=" + str(date.strftime("%Y%m%d")))
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    time.sleep(1)
    for a_tag in soup.findAll("td", class_="ac"):
        text = no_space(a_tag.get_text())
        file.write(text + " , ")
        print(a_tag.get_text().strip().replace("\n", "").replace("\t", ""))

file.close()