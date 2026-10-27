import win32gui
winList = []

def getWinListProc(hwnd, extra):
    global winList
    if win32gui.IsWindowVisible(hwnd):
        text = win32gui.GetWindowText(hwnd)
        if len(text) > 0:
            winList.append((hwnd, text))

def getWinList():
    global winList
    winList = []
    win32gui.EnumWindows(getWinListProc, None)
    for l in winList:
        print(l)

getWinList()
hwnd = input('Type hwnd : ')
win32gui.SetForegroundWindow(int(hwnd))
