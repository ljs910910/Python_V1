import pywinauto as pwa
import pyautogui
import os, time, datetime
from datetime import date, timedelta
import warnings, errno
from PIL import ImageGrab

warnings.simplefilter('ignore', category=UserWarning)

#-------------------------------------------------------------------------------
# TACS Focus
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

#-------------------------------------------------------------------------------
# TACS Control
#-------------------------------------------------------------------------------
def TACS_Control():
    IOI()
    time.sleep(1)
    rins_find_btn = pyautogui.locateOnScreen('find_btn.png')
    pyautogui.moveTo(rins_find_btn)
    pyautogui.click()
    time.sleep(1)
    rins_find_btn1 = pyautogui.locateOnScreen('total_search.png')
    pyautogui.moveTo(rins_find_btn1)
    pyautogui.moveRel(70, 0)
    pyautogui.click()
    time.sleep(1)
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.typewrite('rins-v-prox01')
    pyautogui.hotkey('enter')
    time.sleep(1)
    pyautogui.moveRel(0, 90)
    pyautogui.doubleClick()
    time.sleep(5)
    pyautogui.hotkey('win', 'up')
    time.sleep(1)

# -------------------------------------------------------------------------------
# capture
# -------------------------------------------------------------------------------
def Capture():
    img = ImageGrab.grab()
    img.save('./rins_image/' + str(rins_server_list1) + '.png')
    time.sleep(2)

def DB_Capture():
    img = ImageGrab.grab()
    img.save('./rins_image/' + str(rins_server_list2) + '.png')
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
    # print(yesterday2)
    return yesterday2

# -------------------------------------------------------------------------------
# rins pw
# -------------------------------------------------------------------------------
def rins_pw():
    pyautogui.typewrite('ssh rinsop@' + rins_server_list)
    pyautogui.hotkey('enter')
    time.sleep(2)
    pyautogui.typewrite('passwd')
    pyautogui.hotkey('enter')
    time.sleep(2)
    pyautogui.typewrite('clear')
    pyautogui.hotkey('enter')

# -------------------------------------------------------------------------------
# create dir
# -------------------------------------------------------------------------------
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

# -------------------------------------------------------------------------------
# 서버 점검
# -------------------------------------------------------------------------------
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
    pyautogui.typewrite('tail -f /data/logs/WS_SPPS_J_0.log.' + today())
    pyautogui.hotkey('enter')
    time.sleep(10)
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(2)
    pyautogui.typewrite('tail -f /data/logs/WS_SPPS_J_1.log.' + today())
    pyautogui.hotkey('enter')
    time.sleep(10)
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(2)

    pyautogui.typewrite('zgrep -i \'exception\' /data/logs/WS_SPPS_J_0.log.' + yesterday() + '.gz')
    pyautogui.hotkey('enter')
    time.sleep(30)
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(2)

    pyautogui.typewrite('grep -i \'exception\' /data/logs/WS_SPPS_J_0.log.' + today())
    pyautogui.hotkey('enter')
    time.sleep(20)
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(2)

    pyautogui.typewrite('zgrep -i \'exception\' /data/logs/WS_SPPS_J_1.log.' + yesterday() + '.gz')
    pyautogui.hotkey('enter')
    time.sleep(30)
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(2)

    pyautogui.typewrite('grep -i \'exception\' /data/logs/WS_SPPS_J_1.log.' + today())
    pyautogui.hotkey('enter')
    time.sleep(20)
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(2)

    pyautogui.typewrite('zgrep -i \'error\' /data/logs/WS_SPPS_J_0.log.' + yesterday() + '.gz' + ' | zegrep -v \'already|ASH ISLAND-M/V|invalid|found\'')
    pyautogui.hotkey('enter')
    time.sleep(30)
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(2)

    pyautogui.typewrite('grep -i \'error\' /data/logs/WS_SPPS_J_0.log.' + today() + ' | egrep -v \'already|ASH ISLAND-M/V|invalid|found\'')
    pyautogui.hotkey('enter')
    time.sleep(20)
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(2)

    pyautogui.typewrite('zgrep -i \'error\' /data/logs/WS_SPPS_J_1.log.' + yesterday() + '.gz' + ' | zegrep -v \'already|ASH ISLAND-M/V|invalid|found\'')
    pyautogui.hotkey('enter')
    time.sleep(30)
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(2)

    pyautogui.typewrite('grep -i \'error\' /data/logs/WS_SPPS_J_1.log.' + today() + ' | egrep -v \'already|ASH ISLAND-M/V|invalid|found\'')
    pyautogui.hotkey('enter')
    time.sleep(20)
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(2)
    pyautogui.typewrite('date; mpstat | tail -1 | awk \'{print 100-$NF}\'; free -m; df -h')
    pyautogui.hotkey('enter')
    time.sleep(1)
    Capture()
    if cnt == 1:
        while cnt < 2:
            cnt += 1
            rins_server_list = f1.readline().rstrip()
            rins_server_list1 = f2.readline().rstrip()
            rins_server_list3 = f4.readline().rstrip()
            print(rins_server_list1)
            rins_pw()
            time.sleep(1)
            pyautogui.typewrite('tail -f /data/logs/SPPS_J_0.log.' + today())
            pyautogui.hotkey('enter')
            time.sleep(10)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(2)
            pyautogui.typewrite('tail -f /data/logs/SPPS_J_1.log.' + today())
            pyautogui.hotkey('enter')
            time.sleep(10)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(2)

            pyautogui.typewrite('zgrep -i \'exception\' /data/logs/SPPS_J_0.log.' + yesterday() + '.gz')
            pyautogui.hotkey('enter')
            time.sleep(30)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(2)

            pyautogui.typewrite('grep -i \'exception\' /data/logs/SPPS_J_0.log.' + today())
            pyautogui.hotkey('enter')
            time.sleep(20)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(2)

            pyautogui.typewrite('zgrep -i \'exception\' /data/logs/SPPS_J_1.log.' + yesterday() + '.gz')
            pyautogui.hotkey('enter')
            time.sleep(30)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(2)

            pyautogui.typewrite('grep -i \'exception\' /data/logs/SPPS_J_1.log.' + today())
            pyautogui.hotkey('enter')
            time.sleep(20)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(2)

            pyautogui.typewrite('zgrep -i \'error\' /data/logs/SPPS_J_0.log.' + yesterday() + '.gz' + ' | zegrep -v \'already|invalid|found|{}\'')
            pyautogui.hotkey('enter')
            time.sleep(30)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(2)

            pyautogui.typewrite('grep -i \'error\' /data/logs/SPPS_J_0.log.' + today() + ' | egrep -v \'already|invalid|found|{}\'')
            pyautogui.hotkey('enter')
            time.sleep(20)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(2)

            pyautogui.typewrite('zgrep -i \'error\' /data/logs/SPPS_J_1.log.' + yesterday() + '.gz' + ' | zegrep -v \'already|invalid|found|{}\'')
            pyautogui.hotkey('enter')
            time.sleep(30)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(2)

            pyautogui.typewrite('grep -i \'error\' /data/logs/SPPS_J_1.log.' + today() + ' | egrep -v \'already|invalid|found|{}\'')
            pyautogui.hotkey('enter')
            time.sleep(20)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(2)
            pyautogui.typewrite('date; mpstat | tail -1 | awk \'{print 100-$NF}\'; free -m; df -h')
            pyautogui.hotkey('enter')
            time.sleep(1)
            Capture()
            if cnt == 2:
                while cnt < 7:
                    cnt += 1
                    rins_server_list = f1.readline().rstrip()
                    rins_server_list1 = f2.readline().rstrip()
                    rins_server_list3 = f4.readline().rstrip()
                    print(rins_server_list1)
                    rins_pw()
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
                    if cnt == 7:
                        while cnt < 9:
                            cnt += 1
                            rins_server_list = f1.readline().rstrip()
                            rins_server_list1 = f2.readline().rstrip()
                            rins_server_list3 = f4.readline().rstrip()
                            print(rins_server_list1)
                            rins_pw()
                            time.sleep(1)
                            pyautogui.typewrite('vi /data/logs/batch/batch.log')
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
                            pyautogui.typewrite('cat /data/logs/batch/batch-error.log')
                            pyautogui.hotkey('enter')
                            time.sleep(2)
                            pyautogui.typewrite('date; mpstat | tail -1 | awk \'{print 100-$NF}\'; free -m; df -h')
                            pyautogui.hotkey('enter')
                            time.sleep(1)
                            Capture()
                            if cnt == 9:
                                while cnt < 10:
                                    cnt += 1
                                    rins_server_list = f1.readline().rstrip()
                                    rins_server_list1 = f2.readline().rstrip()
                                    rins_server_list3 = f4.readline().rstrip()
                                    print(rins_server_list1)
                                    rins_pw()
                                    time.sleep(1)
                                    pyautogui.typewrite('tail -f /data/logs/spcs/spcs.' + today() + '.log')
                                    pyautogui.hotkey('enter')
                                    time.sleep(10)
                                    pyautogui.hotkey('ctrl', 'c')
                                    time.sleep(1)
                                    pyautogui.typewrite('cat /data/logs/spcs/spcs.' + today() + '.log | grep -i \'exception\'')
                                    pyautogui.hotkey('enter')
                                    time.sleep(20)
                                    pyautogui.hotkey('ctrl', 'c')
                                    time.sleep(1)

                                    pyautogui.typewrite('cat /data/logs/spcs/spcs.' + yesterday() + '.log | grep -i \'exception\'')
                                    pyautogui.hotkey('enter')
                                    time.sleep(20)
                                    pyautogui.hotkey('ctrl', 'c')
                                    time.sleep(1)

                                    pyautogui.typewrite('date; mpstat | tail -1 | awk \'{print 100-$NF}\'; free -m; df -h')
                                    pyautogui.hotkey('enter')
                                    time.sleep(1)
                                    Capture()
                                    if cnt == 10:
                                        while cnt < 11:
                                            cnt += 1
                                            rins_server_list = f1.readline().rstrip()
                                            rins_server_list1 = f2.readline().rstrip()
                                            rins_server_list3 = f4.readline().rstrip()
                                            print(rins_server_list1)
                                            rins_pw()
                                            time.sleep(1)
                                            pyautogui.typewrite('tail -f /data/logs/push/push.' + today() + '.log')
                                            pyautogui.hotkey('enter')
                                            time.sleep(10)
                                            pyautogui.hotkey('ctrl', 'c')
                                            time.sleep(1)
                                            pyautogui.typewrite('cat /data/logs/push/push.' + today() + '.log | grep -i \'exception\'')
                                            pyautogui.hotkey('enter')
                                            time.sleep(20)
                                            pyautogui.hotkey('ctrl', 'c')
                                            time.sleep(1)

                                            pyautogui.typewrite('cat /data/logs/push/push.' + yesterday() + '.log | grep -i \'exception\'')
                                            pyautogui.hotkey('enter')
                                            time.sleep(20)
                                            pyautogui.hotkey('ctrl', 'c')
                                            time.sleep(1)

                                            pyautogui.typewrite('date; mpstat | tail -1 | awk \'{print 100-$NF}\'; free -m; df -h')
                                            pyautogui.hotkey('enter')
                                            time.sleep(1)
                                            Capture()
                                            if cnt == 11:
                                                while cnt < 12:
                                                    cnt += 1
                                                    rins_server_list = f1.readline().rstrip()
                                                    rins_server_list1 = f2.readline().rstrip()
                                                    rins_server_list3 = f4.readline().rstrip()
                                                    print(rins_server_list1)
                                                    rins_pw()
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

                                                    pyautogui.typewrite('cat /data/logs/spls/spls.' + yesterday() + '.log | grep -i \'exception\'')
                                                    pyautogui.hotkey('enter')
                                                    time.sleep(20)
                                                    pyautogui.hotkey('ctrl', 'c')
                                                    time.sleep(1)

                                                    pyautogui.typewrite('date; mpstat | tail -1 | awk \'{print 100-$NF}\'; free -m; df -h')
                                                    pyautogui.hotkey('enter')
                                                    time.sleep(1)
                                                    Capture()
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
                                                            pyautogui.typewrite('su -')
                                                            pyautogui.hotkey('enter')
                                                            time.sleep(2)
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
                                                            if cnt == 21:
                                                                break
f1.close(); f2.close(); f3.close(); f4.close()
