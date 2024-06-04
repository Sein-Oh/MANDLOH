import win32api
import win32gui


#실행중인 윈도우 목록 가져오기
def get_win_list():
    def callback(hwnd, hwnd_list: list):
        title = win32gui.GetWindowText(hwnd)
        if win32gui.IsWindowEnabled(hwnd) and win32gui.IsWindowVisible(hwnd) and title:
            hwnd_list.append((title, hwnd))
        return True
    output = []
    win32gui.EnumWindows(callback, output)
    return output

#윈도우의 위치 및 크기 가져오기
def get_win_size(hwnd):
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    return left, top, right, bottom

#이름으로 윈도우 찾기
def find_window(target):
    win_ary = get_win_list()
    for win in win_ary:
        if target in win[0]:
            target_text = win[0]
            target_hwnd = win[1]
    return target_hwnd, target_text

#활성화된 윈도우 찾기
def get_foreground():
    hwnd = win32gui.GetForegroundWindow()
    text = win32gui.GetWindowText(hwnd)
    return hwnd, text

#디스플레이 해상도 가져오기
def get_screen_size():
    width = win32api.GetSystemMetrics(0)
    height = win32api.GetSystemMetrics(1)
    return width, height

def set_foreground(hwnd):
    win32gui.SetForegroundWindow(hwnd)
    return
