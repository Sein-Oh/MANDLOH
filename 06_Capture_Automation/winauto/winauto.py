import keyboard
import win32gui, win32api, win32ui
from ctypes import windll
from PIL import ImageGrab, Image

hwnd = None

def getWindow():
    global hwnd
    hwnd = win32gui.GetForegroundWindow()
    text = win32gui.GetWindowText(hwnd)
    print("{0} : {1}".format(hwnd, text))

def setTop():
    global hwnd
    keyboard.press("alt") #to prevent 183 error
    win32gui.SetForegroundWindow(hwnd)
    keyboard.release("alt") #1to prevent 183 error
    
def getColor():
    x, y = win32api.GetCursorPos()
    color = win32gui.GetPixel(win32gui.GetDC(win32gui.GetActiveWindow()), x, y)
    b = color & 255
    g = (color >> 8) & 255
    r = (color >> 16) & 255
    print("RGB : {0}, {1}, {2}".format(r, g, b))

def capImage():
    global hwnd
    dim = win32gui.GetWindowRect(hwnd)
    image = ImageGrab.grab(dim)
    image.show()

def capInactive():
    global hwnd
    left, top, right, bot = win32gui.GetWindowRect(hwnd)
    w = right - left
    h = bot - top
    hwndDC = win32gui.GetWindowDC(hwnd)
    mfcDC  = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()

    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)

    saveDC.SelectObject(saveBitMap)
    result = windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 0)
    print(result)
    bmpinfo = saveBitMap.GetInfo()
    bmpstr = saveBitMap.GetBitmapBits(True)

    im = Image.frombuffer(
        'RGB',
        (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
        bmpstr, 'raw', 'BGRX', 0, 1)

    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwndDC)

    if result == 1:
        im.show()

keyboard.add_hotkey("ctrl+1", lambda: getWindow())
keyboard.add_hotkey("ctrl+2", lambda: setTop())
keyboard.add_hotkey("ctrl+3", lambda: capInactive())
keyboard.wait("esc")
