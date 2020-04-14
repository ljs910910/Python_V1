import pywinauto as pwa
import pyautogui
import os
import time
import warnings
from PIL import ImageGrab

#32bit 64bit 무시
warnings.simplefilter('ignore', category=UserWarning)

#컨트롤이 필요한 프로그램 윈도우 top으로 띄움
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
    t = u'program.*'
    return setFocus(t)

if __name__ == "__main__":
    IOI()

def key_press():
    line1 = f1.readline().rstrip()
    print(line1)
    pyautogui.click(23, 70)
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.typewrite(line1, interval=0.1)
    pyautogui.hotkey('enter')
    time.sleep(2)

    btn = pyautogui.locateOnScreen('btn.png')
    pyautogui.doubleClick(btn)
    time.sleep(2.5)

def passwd_chg():
    time.sleep(1)
    pyautogui.typewrite('1111', interval=0.1)
    pyautogui.hotkey('enter')
    time.sleep(1)
    pyautogui.typewrite('1111', interval=0.1)
    pyautogui.hotkey('enter')
    time.sleep(1)

def capture():
    line2 = f2.readline().rstrip()
    img = ImageGrab.grab()
    img.save('./image/' + str(line2) + '.png')
    time.sleep(1)

try:
    if not (os.path.isdir('image')):
        os.makedirs(os.path.join('image'))
except OSError as e:
    if e.errno != errno.EEXIST:
        print("fail")
        exit()

f1 = open('sphostname1.txt', "r")
f2 = open('sphostname2.txt', "r")

cnt = 0
while cnt < 67:
    cnt += 1
    key_press()
    pyautogui.typewrite('id', interval=0.1)
    pyautogui.hotkey('enter')
    time.sleep(1)
    pyautogui.typewrite('pw')
    pyautogui.hotkey('enter')
    time.sleep(2)

    pyautogui.typewrite('passwd id', interval=0.1)
    pyautogui.hotkey('enter')
    passwd_chg()
    capture()
    pyautogui.typewrite('exit', interval=0.1)
    pyautogui.hotkey('enter')
    time.sleep(1)
    if cnt == 67:
        while cnt < 73:
            cnt += 1
            key_press()
            pyautogui.typewrite('id', interval=0.1)
            pyautogui.hotkey('enter')
            time.sleep(1)
            pyautogui.typewrite('pw')
            pyautogui.hotkey('enter')
            time.sleep(2)

            pyautogui.typewrite('passwd id', interval=0.1)
            pyautogui.hotkey('enter')
            passwd_chg()
            capture()
            pyautogui.typewrite('exit', interval=0.1)
            pyautogui.hotkey('enter')
            time.sleep(1)
            if cnt == 73:
                while cnt < 83:
                    cnt += 1
                    key_press()
                    pyautogui.typewrite('id', interval=0.1)
                    pyautogui.hotkey('enter')
                    time.sleep(1)
                    pyautogui.typewrite('pw')
                    pyautogui.hotkey('enter')
                    time.sleep(2)

                    pyautogui.typewrite('passwd id', interval=0.1)
                    pyautogui.hotkey('enter')
                    passwd_chg()
                    capture()
                    pyautogui.typewrite('exit', interval=0.1)
                    pyautogui.hotkey('enter')
                    time.sleep(1)
                    if cnt == 83: break
f1.close()
f2.close()
