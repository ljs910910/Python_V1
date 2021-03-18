import pywinauto as pwa
import pyautogui
import os
import time
import warnings
import errno
import datetime
from PIL import Image, ImageGrab
import pytesseract
import re
import cv2

warnings.simplefilter('ignore', category=UserWarning)

def setFocus(title_reg):
    app = pwa.application.Application()
    t = title_reg
    print('find title : ' + str(title_reg))
    try:
        handle = pwa.findwindows.find_windows(title_re=t)[0]
        app.connect(handle=handle)
        print('title: ' + str(t) + 'handle: ' + str(handle) + 'Setted')
    except:
        print('No title exist on window')
    window = app.window(handle=handle)
    try:
        window.set_focus()
    except Exception as e:
        print('[error]setFocuse : ' + str(e))
    return window

def IOI():
    t = u'STGClient.*'
    return setFocus(t)

if __name__ == "__main__":
    IOI()
    rins_find_btn = pyautogui.locateOnScreen('rins_find_btn.png')
    pyautogui.moveTo(rins_find_btn)
    pyautogui.moveRel(90, 0)
    pyautogui.click()
    pyautogui.hotkey('enter')
    time.sleep(1)

def TACS_Control():
    rins_find_btn1 = pyautogui.locateOnScreen('rins_find_btn1.png')
    pyautogui.moveTo(rins_find_btn1)
    pyautogui.moveRel(122, 0)
    pyautogui.click()
    time.sleep(1)
    pyautogui.typewrite('rins-v-prox01')
    pyautogui.hotkey('enter')
    time.sleep(1)
    pyautogui.moveRel(0, 70)
    time.sleep(1)
    pyautogui.doubleClick()
    time.sleep(3)
    pyautogui.hotkey('win', 'up')
    time.sleep(1)
    pyautogui.click(100,100, button='right')
    time.sleep(1)
    rins_find_btn2 = pyautogui.locateOnScreen('change_settings.png')
    pyautogui.moveTo(rins_find_btn2)
    pyautogui.click()
    time.sleep(1)
    rins_find_btn3 = pyautogui.locateOnScreen('appearance.png')
    pyautogui.moveTo(rins_find_btn3)
    pyautogui.click()
    time.sleep(1)
    rins_find_btn4 = pyautogui.locateOnScreen('change.png')
    pyautogui.moveTo(rins_find_btn4)
    pyautogui.click()
    time.sleep(2)
    rins_find_btn5 = pyautogui.locateOnScreen('size.png')
    pyautogui.moveTo(rins_find_btn5)
    pyautogui.moveRel(0, 60)
    time.sleep(1)
    pyautogui.click()
    pyautogui.hotkey('enter')
    time.sleep(1)
    rins_find_btn6 = pyautogui.locateOnScreen('apply.png')
    pyautogui.moveTo(rins_find_btn6)
    pyautogui.click()
    time.sleep(1)

def Capture():
    img = ImageGrab.grab()
    img.save('./rins_image/' + str(rins_server_list1) + '.png')
    time.sleep(2)

def DB_Capture():
    img = ImageGrab.grab()
    img.save('./rins_image/' + str(rins_server_list2) + '.png')
    time.sleep(2)

def now_date():
    now = datetime.datetime.now()
    now_dt = now.strftime('%Y-%m-%d')
    return now_dt

def img_modify():
    # hostname_img = cv2.imread('./rins_image/' + str(rins_server_list1) + '.png', cv2.IMREAD_COLOR)
    hostname_img = cv2.imread('./rins_image/' + str(rins_server_list1) + '.png')
    img_cut = hostname_img[23:100, 0:300].copy()
    # img_cut1 = cv2.cvtColor(img_cut, cv2.COLOR_BGR2HLS_FULL)
    height, width = img_cut.shape[:2]
    resize_img = cv2.resize(img_cut, (2 * width, 2 * height), interpolation=cv2.INTER_LANCZOS4)
    img_result = cv2.imwrite('./rins_image/' + str(rins_server_list3) + '.png', 255 - resize_img)
    time.sleep(1)
    return img_result

def OCR():
    OCR = pytesseract.image_to_string(Image.open('./rins_image/' + str(rins_server_list3) + '.png'))
    print(OCR)
    Catch = re.search(str(rins_server_list3), OCR)
    print(Catch)
    return Catch

def rins_pw():
    pyautogui.typewrite('ssh rinsop@' + rins_server_list)
    pyautogui.hotkey('enter')
    time.sleep(1)
    pyautogui.typewrite('passwd')
    pyautogui.hotkey('enter')
    time.sleep(1)
    pyautogui.typewrite('clear')
    pyautogui.hotkey('enter')

try:
    if not (os.path.isdir('rins_image')):
        os.makedirs(os.path.join('rins_image'))
except OSError as e:
    if e.errno != errno.EEXIST:
        print('fail')
        exit()

f1 = open('rins_server_list.txt', 'r')
f2 = open('rins_server_list1.txt', 'r')
f3 = open('rins_server_list2.txt', 'r')
f4 = open('rins_server_list3.txt', 'r')

cnt = 0
while cnt < 1:
    cnt += 1
    rins_server_list1 = f2.readline().rstrip()
    rins_server_list3 = f4.readline().rstrip()
    print(rins_server_list1)
    TACS_Control()
    pyautogui.typewrite('clear')
    pyautogui.hotkey('enter')
    time.sleep(1)
    Capture()
    img_modify()
    if OCR() is not None:
        print('login success')
        time.sleep(1)
        pyautogui.typewrite('tail -f /data/logs/WS_SPPS_J_0.log.' + now_date())
        pyautogui.hotkey('enter')
        time.sleep(10)
        pyautogui.hotkey('ctrl', 'c')
        time.sleep(2)
        pyautogui.typewrite('tail -f /data/logs/WS_SPPS_J_1.log.' + now_date())
        pyautogui.hotkey('enter')
        time.sleep(10)
        pyautogui.hotkey('ctrl', 'c')
        time.sleep(1)
        pyautogui.typewrite('grep -i \'exception\' /data/logs/WS_SPPS_J_0.log.' + now_date())
        pyautogui.hotkey('enter')
        time.sleep(20)
        pyautogui.hotkey('ctrl', 'c')
        time.sleep(2)
        pyautogui.typewrite('grep -i \'exception\' /data/logs/WS_SPPS_J_1.log.' + now_date())
        pyautogui.hotkey('enter')
        time.sleep(20)
        pyautogui.hotkey('ctrl', 'c')
        time.sleep(1)
        pyautogui.typewrite('date; mpstat | tail -1 | awk \'{print 100-$NF}\'; free -m; df -h')
        pyautogui.hotkey('enter')
        time.sleep(1)
        Capture()
    else:
        print('not match, error')
        break
    if cnt == 1:
        while cnt < 2:
            cnt += 1
            rins_server_list = f1.readline().rstrip()
            rins_server_list1 = f2.readline().rstrip()
            rins_server_list3 = f4.readline().rstrip()
            print(rins_server_list1)
            rins_pw()
            time.sleep(1)
            Capture()
            img_modify()
            if OCR() is not None:
                print('login success')
                time.sleep(1)
                pyautogui.typewrite('tail -f /data/logs/SPPS_J_0.log.' + now_date())
                pyautogui.hotkey('enter')
                time.sleep(10)
                pyautogui.hotkey('ctrl', 'c')
                time.sleep(2)
                pyautogui.typewrite('tail -f /data/logs/SPPS_J_1.log.' + now_date())
                pyautogui.hotkey('enter')
                time.sleep(10)
                pyautogui.hotkey('ctrl', 'c')
                time.sleep(1)
                pyautogui.typewrite('grep -i \'exception\' /data/logs/SPPS_J_0.log.' + now_date())
                pyautogui.hotkey('enter')
                time.sleep(20)
                pyautogui.hotkey('ctrl', 'c')
                time.sleep(2)
                pyautogui.typewrite('grep -i \'exception\' /data/logs/SPPS_J_1.log.' + now_date())
                pyautogui.hotkey('enter')
                time.sleep(20)
                pyautogui.hotkey('ctrl', 'c')
                time.sleep(1)
                pyautogui.typewrite('date; mpstat | tail -1 | awk \'{print 100-$NF}\'; free -m; df -h')
                pyautogui.hotkey('enter')
                time.sleep(1)
                Capture()
            else:
                print('not match, error')
                break
            if cnt == 2:
                while cnt < 7:
                    cnt += 1
                    rins_server_list = f1.readline().rstrip()
                    rins_server_list1 = f2.readline().rstrip()
                    rins_server_list3 = f4.readline().rstrip()
                    print(rins_server_list1)
                    rins_pw()
                    time.sleep(1)
                    Capture()
                    img_modify()
                    if OCR() is not None:
                        print('login success')
                        time.sleep(1)
                        pyautogui.typewrite('tail -f /data/logs/kafka/kafka.log')
                        pyautogui.hotkey('enter')
                        time.sleep(10)
                        pyautogui.hotkey('ctrl', 'c')
                        time.sleep(1)
                        pyautogui.typewrite('ls -alh /data/logs/kafka/kafka-error.log')
                        pyautogui.hotkey('enter')
                        time.sleep(1)
                        pyautogui.typewrite('date; mpstat | tail -1 | awk \'{print 100-$NF}\'; free -m; df -h')
                        pyautogui.hotkey('enter')
                        time.sleep(1)
                        Capture()
                    else:
                        print('not match, error')
                        break
                    if cnt == 7:
                        while cnt < 9:
                            cnt += 1
                            rins_server_list = f1.readline().rstrip()
                            rins_server_list1 = f2.readline().rstrip()
                            rins_server_list3 = f4.readline().rstrip()
                            print(rins_server_list1)
                            rins_pw()
                            time.sleep(1)
                            Capture()
                            img_modify()
                            if OCR() is not None:
                                print('login success')
                                time.sleep(1)
                                pyautogui.typewrite('vi /data/logs/batch/batch.log')
                                pyautogui.hotkey('enter')
                                time.sleep(1)
                                pyautogui.typewrite('gg')
                                time.sleep(4)
                                for batch_cnt in range(0,9):
                                    batch_cnt = pyautogui.hotkey('ctrl', 'f')
                                    time.sleep(4)
                                pyautogui.hotkey('shift', ':')
                                time.sleep(1)
                                pyautogui.typewrite('q!')
                                pyautogui.hotkey('enter')
                                time.sleep(1)
                                pyautogui.typewrite('cat /data/logs/batch/batch-error.log')
                                pyautogui.hotkey('enter')
                                time.sleep(2)
                                pyautogui.typewrite('date; mpstat | tail -1 | awk \'{print 100-$NF}\'; free -m; df -h')
                                pyautogui.hotkey('enter')
                                time.sleep(1)
                                Capture()
                            else:
                                print('not match, error')
                                break
                            if cnt == 9:
                                while cnt < 10:
                                    cnt += 1
                                    rins_server_list = f1.readline().rstrip()
                                    rins_server_list1 = f2.readline().rstrip()
                                    rins_server_list3 = f4.readline().rstrip()
                                    print(rins_server_list1)
                                    rins_pw()
                                    time.sleep(1)
                                    Capture()
                                    img_modify()
                                    if OCR() is not None:
                                        print('login success')
                                        time.sleep(1)
                                        pyautogui.typewrite('tail -f /data/logs/spcs/spcs.' + now_date() + '.log')
                                        pyautogui.hotkey('enter')
                                        time.sleep(10)
                                        pyautogui.hotkey('ctrl', 'c')
                                        time.sleep(1)
                                        pyautogui.typewrite('cat /data/logs/spcs/spcs.' + now_date() + '.log | grep -i \'exception\'')
                                        pyautogui.hotkey('enter')
                                        time.sleep(20)
                                        pyautogui.hotkey('ctrl', 'c')
                                        time.sleep(1)
                                        pyautogui.typewrite('date; mpstat | tail -1 | awk \'{print 100-$NF}\'; free -m; df -h')
                                        pyautogui.hotkey('enter')
                                        time.sleep(1)
                                        Capture()
                                    else:
                                        print('not match, error')
                                        break
                                    if cnt == 10:
                                        while cnt < 11:
                                            cnt += 1
                                            rins_server_list = f1.readline().rstrip()
                                            rins_server_list1 = f2.readline().rstrip()
                                            rins_server_list3 = f4.readline().rstrip()
                                            print(rins_server_list1)
                                            rins_pw()
                                            time.sleep(1)
                                            Capture()
                                            img_modify()
                                            if OCR() is not None:
                                                print('login success')
                                                time.sleep(1)
                                                pyautogui.typewrite('tail -f /data/logs/push/push.' + now_date() + '.log')
                                                pyautogui.hotkey('enter')
                                                time.sleep(10)
                                                pyautogui.hotkey('ctrl', 'c')
                                                time.sleep(1)
                                                pyautogui.typewrite('cat /data/logs/push/push.' + now_date() + '.log | grep -i \'exception\'')
                                                pyautogui.hotkey('enter')
                                                time.sleep(20)
                                                pyautogui.hotkey('ctrl', 'c')
                                                time.sleep(1)
                                                pyautogui.typewrite('date; mpstat | tail -1 | awk \'{print 100-$NF}\'; free -m; df -h')
                                                pyautogui.hotkey('enter')
                                                time.sleep(1)
                                                Capture()
                                            else:
                                                print('not match, error')
                                                break
                                            if cnt == 11:
                                                while cnt < 12:
                                                    cnt += 1
                                                    rins_server_list = f1.readline().rstrip()
                                                    rins_server_list1 = f2.readline().rstrip()
                                                    rins_server_list3 = f4.readline().rstrip()
                                                    print(rins_server_list1)
                                                    rins_pw()
                                                    time.sleep(1)
                                                    Capture()
                                                    img_modify()
                                                    if OCR() is not None:
                                                        print('login success')
                                                        time.sleep(1)
                                                        pyautogui.typewrite('tail -f /data/logs/spls/spls.log')
                                                        pyautogui.hotkey('enter')
                                                        time.sleep(10)
                                                        pyautogui.hotkey('ctrl', 'c')
                                                        time.sleep(1)
                                                        pyautogui.typewrite('cat /data/logs/spls/spls.log | grep -i \'exception\'')
                                                        pyautogui.hotkey('enter')
                                                        time.sleep(20)
                                                        pyautogui.hotkey('ctrl', 'c')
                                                        time.sleep(1)
                                                        pyautogui.typewrite('date; mpstat | tail -1 | awk \'{print 100-$NF}\'; free -m; df -h')
                                                        pyautogui.hotkey('enter')
                                                        time.sleep(1)
                                                        Capture()
                                                    else:
                                                        print('not match, error')
                                                        break
                                                    if cnt == 12:
                                                        while cnt < 21:
                                                            cnt += 1
                                                            rins_server_list = f1.readline().rstrip()
                                                            rins_server_list1 = f2.readline().rstrip()
                                                            rins_server_list2 = f3.readline().rstrip()
                                                            rins_server_list3 = f4.readline().rstrip()
                                                            print(rins_server_list1)
                                                            rins_pw()
                                                            time.sleep(1)
                                                            Capture()
                                                            img_modify()
                                                            if OCR() is not None:
                                                                print('login success')
                                                                time.sleep(1)
                                                                pyautogui.typewrite('su -')
                                                                pyautogui.hotkey('enter')
                                                                time.sleep(1)
                                                                pyautogui.typewrite('passwd')
                                                                pyautogui.hotkey('enter')
                                                                time.sleep(1)
                                                                pyautogui.typewrite('su - mysql')
                                                                pyautogui.hotkey('enter')
                                                                time.sleep(1)
                                                                pyautogui.typewrite('sql')
                                                                pyautogui.hotkey('enter')
                                                                time.sleep(1)
                                                                pyautogui.typewrite('show slave status\G;')
                                                                time.sleep(1)
                                                                pyautogui.hotkey('enter')
                                                                time.sleep(1)
                                                                DB_Capture()
                                                                pyautogui.typewrite('quit')
                                                                pyautogui.hotkey('enter')
                                                                time.sleep(1)
                                                                pyautogui.typewrite('exit')
                                                                pyautogui.hotkey('enter')
                                                                time.sleep(1)
                                                                pyautogui.typewrite('exit')
                                                                pyautogui.hotkey('enter')
                                                                time.sleep(1)
                                                                pyautogui.typewrite('date; mpstat | tail -1 | awk \'{print 100-$NF}\'; free -m; df -h')
                                                                pyautogui.hotkey('enter')
                                                                time.sleep(1)
                                                                Capture()
                                                            else:
                                                                print('not match, error')
                                                                break
                                                            if cnt == 21:
                                                                break
f1.close(); f2.close(); f3.close(); f4.close()

