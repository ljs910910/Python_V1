from bs4 import BeautifulSoup
from pprint import pprint
from selenium import webdriver
import re
#import csv
#import openpyxl

#불필요한 공백 제거
def no_space(text):
    text1 = re.sub('\n | \t | \r', '', text)
    text2 = re.sub('\n', '', text1)
    return text2

#웹 페이지 로그인
driver = webdriver.Chrome(r"C:\Users\Downloads\chromedriver_win32\chromedriver.exe")
driver.get("http://211.1.1.1/spa/account/login.do")
driver.find_element_by_name("j_username").send_keys("we")
driver.find_element_by_name("j_password").send_keys("we1234")
driver.find_element_by_xpath("""//*[@id="loginForm"]/fieldset/p/input""").click()

#크롤링 주소
driver.get("http://211.1.1.1/spa/user/services/push/list.do")
html = driver.page_source
soup = BeautifulSoup(html, "html.parser")

file = open('test1.csv', 'w', newline='')

#데이터 엑셀 저장 및 출력 확인
for a_tag in soup.findAll("td", class_="al td_title"):
    text = no_space(a_tag.get_text())
    file.write(text + ' , ')
    pprint(text)

file.close()