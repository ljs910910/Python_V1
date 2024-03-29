import pywinauto as pwa
import pyautogui
import os, time, errno, warnings, datetime
from PIL import ImageGrab
from datetime import date, timedelta
#import pytesseract
#import re

warnings.simplefilter('ignore', category=UserWarning)

#-------------------------------------------------------------------------------
# HIWARE Focus
#-------------------------------------------------------------------------------
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
    t = u'HIWARE.*'
    return setFocus(t)

if __name__ == "__main__":
    IOI()
    find_btn = pyautogui.locateOnScreen('find_btn.png')
    pyautogui.moveTo(find_btn)
    pyautogui.click()

#-------------------------------------------------------------------------------
# HIWARE Control
#-------------------------------------------------------------------------------
def Hiware_Control():
    server_input_btn = pyautogui.locateOnScreen('server_input_btn.png')
    pyautogui.moveTo(server_input_btn)
    pyautogui.moveRel(70, 0)
    pyautogui.click()
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.typewrite(server_list)
    pyautogui.hotkey('enter')
    time.sleep(1)
    pyautogui.moveRel(0, 90)
    pyautogui.doubleClick()
    time.sleep(4)
    pyautogui.typewrite('passwd')
    pyautogui.hotkey('enter')
    time.sleep(5)
    pyautogui.hotkey('win', 'up')
    time.sleep(1)

def tcom_Control():
    server_input_btn = pyautogui.locateOnScreen('server_input_btn.png')
    pyautogui.moveTo(server_input_btn)
    pyautogui.moveRel(70, 0)
    pyautogui.click()
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.typewrite(server_list)
    pyautogui.hotkey('enter')
    time.sleep(1)
    pyautogui.moveRel(0, 90)
    pyautogui.doubleClick()
    time.sleep(4)
    pyautogui.typewrite('passwd')
    pyautogui.hotkey('enter')
    time.sleep(7)
    pyautogui.hotkey('enter')
    time.sleep(1)
    pyautogui.hotkey('enter')
    pyautogui.hotkey('win', 'up')
    time.sleep(1)

# -------------------------------------------------------------------------------
# capture
# -------------------------------------------------------------------------------
def Capture():
    img = ImageGrab.grab()
    img.save('./sp_image/' + str(server_list) + '.png')
    time.sleep(2)

# -------------------------------------------------------------------------------
# date
# -------------------------------------------------------------------------------
def today():
    now = datetime.datetime.now()
    now_dt = now.strftime('%Y-%m-%d')
    return now_dt

def yesterday():
    yesterday1 = date.today() - timedelta(1)
    yesterday2 = yesterday1.strftime('%Y-%m-%d')
    return yesterday2

# -------------------------------------------------------------------------------
# OCR
# -------------------------------------------------------------------------------
# def OCR():
#     OCR = pytesseract.image_to_string(Image.open('./sp_image/' + server_list + '.png'))
#     Catch = re.search('$', OCR)
#     print(Catch)
#     return Catch

# -------------------------------------------------------------------------------
# create dir
# -------------------------------------------------------------------------------
try:
    if not (os.path.isdir('sp_image')):
        os.makedirs(os.path.join('sp_image'))
except OSError as e:
    if e.errno != errno.EEXIST:
        print('fail')
        exit()

f1 = open('serverlist.txt', 'r')

# -------------------------------------------------------------------------------
# 서버 점검
# -------------------------------------------------------------------------------
cnt = 0
while cnt < 15:
    cnt += 1
    server_list = f1.readline().rstrip()
    print(server_list)
    Hiware_Control()
    time.sleep(1)
    pyautogui.typewrite('tail -f /home/server/spps/logs/SPPS_J_0.log.' + today())
    pyautogui.hotkey('enter')
    time.sleep(15)
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(1)
    pyautogui.typewrite('cat /home/server/spps/logs/SPPS_J_0.log.' + today() + '| grep -i \'exception\' | grep -v \'CLUSTERDOWN The cluster is down\' ')
    pyautogui.hotkey('enter')
    time.sleep(5)
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(1)
    pyautogui.typewrite('date; mpstat | tail -1 | awk \'{print 100-$NF}\'; free -m; df -h')
    pyautogui.hotkey('enter')
    time.sleep(2)
    Capture()
    pyautogui.typewrite('exit')
    pyautogui.hotkey('enter')
    time.sleep(2)
    if cnt == 15:
        while cnt < 28:
            cnt += 1
            server_list = f1.readline().rstrip()
            print(server_list)
            Hiware_Control()
            time.sleep(1)
            pyautogui.typewrite('tail -f /home/server/spps/logs/WS_SPPS_J_0.log.' + today())
            pyautogui.hotkey('enter')
            time.sleep(15)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(1)
            pyautogui.typewrite('cat /home/server/spps/backup/logs/' + yesterday() + '.txt')
            pyautogui.hotkey('enter')
            time.sleep(3)
            pyautogui.typewrite('date; mpstat | tail -1 | awk \'{print 100-$NF}\'; free -m; df -h')
            pyautogui.hotkey('enter')
            time.sleep(2)
            Capture()
            pyautogui.typewrite('exit')
            pyautogui.hotkey('enter')
            time.sleep(2)
            if cnt == 28:
                while cnt < 36:
                    cnt += 1
                    server_list = f1.readline().rstrip()
                    print(server_list)
                    Hiware_Control()
                    time.sleep(1)
                    pyautogui.typewrite('/home/server/mysql/bin/mysql -u root -p')
                    pyautogui.hotkey('enter')
                    time.sleep(1)
                    pyautogui.typewrite('k2k@admin')
                    pyautogui.hotkey('enter')
                    time.sleep(1)
                    pyautogui.typewrite('show slave status\G;')
                    pyautogui.hotkey('enter')
                    time.sleep(1)
                    Capture()
                    pyautogui.typewrite('exit')
                    pyautogui.hotkey('enter')
                    time.sleep(1)
                    pyautogui.typewrite('exit')
                    pyautogui.hotkey('enter')
                    time.sleep(2)
                    if cnt == 36:
                        while cnt < 41:
                            cnt += 1
                            server_list = f1.readline().rstrip()
                            print(server_list)
                            Hiware_Control()
                            time.sleep(1)
                            pyautogui.hotkey('ctrl', 'u')
                            time.sleep(1)
                            pyautogui.typewrite('tail -f /home/server/tomcat/logs/spcs/spcs.' + today() + '.log')
                            pyautogui.hotkey('enter')
                            time.sleep(10)
                            pyautogui.hotkey('ctrl', 'c')
                            time.sleep(1)
                            pyautogui.typewrite('cat /home/server/tomcat/logs/spcs/spcs.' + today() + '.log' + '| grep -i \'exception\' | grep -v \'CLUSTERDOWN The cluster is down\' ')
                            pyautogui.hotkey('enter')
                            time.sleep(20)
                            pyautogui.hotkey('ctrl', 'c')
                            pyautogui.typewrite('date; mpstat | tail -1 | awk \'{print 100-$NF}\'; free -m; df -h')
                            pyautogui.hotkey('enter')
                            time.sleep(2)
                            Capture()
                            pyautogui.typewrite('exit')
                            pyautogui.hotkey('enter')
                            time.sleep(2)
                            if cnt == 41:
                                while cnt < 43:
                                    cnt += 1
                                    server_list = f1.readline().rstrip()
                                    print(server_list)
                                    Hiware_Control()
                                    pyautogui.hotkey('ctrl', 'u')
                                    time.sleep(1)
                                    time.sleep(1)
                                    pyautogui.typewrite('tail -f /home/server/tomcat/logs/spns/spns.' + today() + '.log')
                                    pyautogui.hotkey('enter')
                                    time.sleep(5)
                                    pyautogui.hotkey('ctrl', 'c')
                                    time.sleep(1)

                                    pyautogui.typewrite('cat /home/server/tomcat/logs/spns/spns.' + today() + '.log' + '| grep -i \'exception\' | grep -v \'HTTP Status 404\' ')
                                    pyautogui.hotkey('enter')
                                    time.sleep(5)
                                    pyautogui.hotkey('ctrl', 'c')
                                    time.sleep(1)

                                    pyautogui.typewrite('cat /home/server/tomcat/logs/spns/spns.' + yesterday() + '.log' + '| grep -i \'exception\' | grep -v \'HTTP Status 404\' ')
                                    pyautogui.hotkey('enter')
                                    time.sleep(5)
                                    pyautogui.hotkey('ctrl', 'c')
                                    time.sleep(1)

                                    pyautogui.typewrite('date; mpstat | tail -1 | awk \'{print 100-$NF}\'; free -m; df -h')
                                    pyautogui.hotkey('enter')
                                    time.sleep(2)
                                    Capture()
                                    pyautogui.typewrite('exit')
                                    pyautogui.hotkey('enter')
                                    time.sleep(2)
                                    if cnt == 43:
                                        while cnt < 47:
                                            cnt += 1
                                            server_list = f1.readline().rstrip()
                                            print(server_list)
                                            tcom_Control()
                                            time.sleep(1)
                                            pyautogui.hotkey('ctrl', 'u')
                                            time.sleep(1)
                                            pyautogui.typewrite('tail -50f /home/server/tomcat/logs/spis.log')
                                            pyautogui.hotkey('enter')
                                            time.sleep(5)
                                            pyautogui.hotkey('ctrl', 'c')
                                            pyautogui.hotkey('ctrl', 'u')
                                            time.sleep(1)
                                            pyautogui.typewrite('tail -50f /home/server/tomcat/logs/trp/trp.' + today() + '.log')
                                            pyautogui.hotkey('enter')
                                            time.sleep(5)
                                            pyautogui.hotkey('ctrl', 'c')
                                            pyautogui.hotkey('ctrl', 'u')
                                            time.sleep(1)
                                            pyautogui.typewrite('date; mpstat | tail -1 | awk \'{print 100-$NF}\'; free -m; df -h')
                                            pyautogui.hotkey('enter')
                                            time.sleep(2)
                                            Capture()
                                            pyautogui.typewrite('exit')
                                            pyautogui.hotkey('enter')
                                            time.sleep(2)
                                            if cnt == 47:
                                                while cnt < 49:
                                                    cnt += 1
                                                    server_list = f1.readline().rstrip()
                                                    print(server_list)
                                                    tcom_Control()
                                                    time.sleep(1)
                                                    pyautogui.typewrite('vi /home/server/tomcat/logs/batch-error.log')
                                                    pyautogui.hotkey('enter')
                                                    time.sleep(1)
                                                    pyautogui.typewrite('gg')
                                                    time.sleep(4)
                                                    for batch_cnt in range(0, 9):
                                                        batch_cnt = pyautogui.hotkey('ctrl', 'f')
                                                        time.sleep(4)
                                                    pyautogui.hotkey('shift', ':')
                                                    time.sleep(1)
                                                    pyautogui.typewrite('q!')
                                                    pyautogui.hotkey('enter')
                                                    time.sleep(1)
                                                    pyautogui.typewrite('date; mpstat | tail -1 | awk \'{print 100-$NF}\'; free -m; df -h')
                                                    pyautogui.hotkey('enter')
                                                    time.sleep(2)
                                                    Capture()
                                                    pyautogui.typewrite('exit')
                                                    pyautogui.hotkey('enter')
                                                    time.sleep(2)
                                                    if cnt == 49:
                                                        print('****maintenance finish****')
                                                        break
f1.close()
