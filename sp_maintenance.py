import pywinauto as pwa
import pyautogui
import os
import time
import warnings
import errno
from PIL import ImageGrab
import datetime

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
    t = u'HIWARE.*'
    return setFocus(t)

if __name__ == "__main__":
    IOI()

def Hiware_Control():
    btn = pyautogui.locateOnScreen('hiware.png')
    pyautogui.moveTo(btn)
    pyautogui.moveRel(70, 0)
    pyautogui.click()
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.typewrite(line2, interval=0.1)
    pyautogui.hotkey('enter')
    time.sleep(1)
    pyautogui.moveRel(0, 90)
    pyautogui.doubleClick()
    time.sleep(3)
    pyautogui.typewrite('Ehdwkrrn!@34', interval=0.1)
    pyautogui.hotkey('enter')
    time.sleep(5)

def NAS_tcom():
    btn = pyautogui.locateOnScreen('hiware.png')
    pyautogui.moveTo(btn)
    pyautogui.moveRel(70, 0)
    pyautogui.click()
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.typewrite(line2, interval=0.1)
    pyautogui.hotkey('enter')
    time.sleep(1)
    pyautogui.moveRel(0, 90)
    pyautogui.doubleClick()
    time.sleep(3)
    pyautogui.typewrite('Ehdwkrrn!@34', interval=0.1)
    pyautogui.hotkey('enter')
    time.sleep(7)
    pyautogui.hotkey('enter')
    time.sleep(1)
    pyautogui.hotkey('enter')

try:
    if not (os.path.isdir('image')):
        os.makedirs(os.path.join('image'))
except OSError as e:
    if e.errno != errno.EEXIST:
        print("fail")
        exit()

def Capture():
    img = ImageGrab.grab()
    img.save('./image/' + str(line2) + '.png')
    time.sleep(3)

def now_date():
    now = datetime.datetime.now()
    now_dt = now.strftime('%Y-%m-%d')
    return now_dt

f1 = open('serverlist.txt', "r")
cnt = 0
while cnt < 15:
    cnt += 1
    line2 = f1.readline().rstrip()
    print(line2)
    Hiware_Control()
    pyautogui.hotkey('win', 'up')
    time.sleep(3)
    pyautogui.typewrite('tail -f /home/server/spps/logs/SPPS_J_0.log.' + now_date())
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
            line2 = f1.readline().rstrip()
            print(line2)
            Hiware_Control()
            pyautogui.hotkey('win', 'up')
            time.sleep(2)
            pyautogui.typewrite('tail -f /home/server/spps/logs/WS_SPPS_J_0.log.' + now_date())
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
            if cnt == 28:
                while cnt < 36:
                    cnt += 1
                    line2 = f1.readline().rstrip()
                    print(line2)
                    Hiware_Control()
                    pyautogui.hotkey('win', 'up')
                    time.sleep(2)
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
                            line2 = f1.readline().rstrip()
                            print(line2)
                            Hiware_Control()
                            pyautogui.hotkey('win', 'up')
                            time.sleep(2)
                            pyautogui.typewrite('tail -f /home/server/tomcat/logs/spcs/spcs.' + now_date() + '.log')
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
                            if cnt == 41:
                                while cnt < 43:
                                    cnt += 1
                                    line2: str = f1.readline().rstrip()
                                    print(line2)
                                    Hiware_Control()
                                    pyautogui.hotkey('win', 'up')
                                    time.sleep(2)
                                    pyautogui.typewrite('tail -f /home/server/tomcat/logs/spns/spns.' + now_date() + '.log')
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
                                            line2 = f1.readline().rstrip()
                                            print(line2)
                                            NAS_tcom()
                                            pyautogui.hotkey('win', 'up')
                                            time.sleep(2)
                                            pyautogui.typewrite('tail -50f /home/server/tomcat/logs/spis.log')
                                            pyautogui.hotkey('enter')
                                            time.sleep(5)
                                            pyautogui.hotkey('ctrl', 'c')
                                            pyautogui.typewrite('tail -50f /home/server/tomcat/logs/trp/trp.' + now_date() + '.log')
                                            pyautogui.hotkey('enter')
                                            time.sleep(5)
                                            pyautogui.hotkey('ctrl', 'c')
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
                                                    line2 = f1.readline().rstrip()
                                                    print(line2)
                                                    NAS_tcom()
                                                    pyautogui.hotkey('win', 'up')
                                                    time.sleep(2)
                                                    pyautogui.typewrite('tail -100f /home/server/tomcat/logs/batch.log')
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
                                                    if cnt == 49:
                                                        print('****maintenance finish****')
                                                        break
f1.close()
