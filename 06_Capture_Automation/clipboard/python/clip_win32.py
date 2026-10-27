import win32clipboard
import time

def get_clip():
    win32clipboard.OpenClipboard()
    try:
        data = win32clipboard.GetClipboardData()
    except:
        data = ""
    win32clipboard.CloseClipboard()
    return data

def set_clip(data):
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardText(data)
    win32clipboard.CloseClipboard()

while True:
    val = get_clip()
    if val == "q": break
    elif val == "check":
        set_clip("check-ok")
    
    time.sleep(0.2)