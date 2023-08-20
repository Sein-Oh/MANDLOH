import win32gui
import win32com.client

# window handle로 창 앞으로 가져오기:
shell = win32com.client.Dispatch("WScript.Shell")
def set_foreground(handle):
    shell.SendKeys('%')
    win32gui.SetForegroundWindow(handle)

# 윈도우에 실행중인 모든 창의 Text, handle을 list로 반환.
def get_win_list():
    def callback(hwnd, hwnd_list: list):
        title = win32gui.GetWindowText(hwnd)
        if win32gui.IsWindowEnabled(hwnd) and win32gui.IsWindowVisible(hwnd) and title:
            hwnd_list.append((title, hwnd))
        return True
    output = []
    win32gui.EnumWindows(callback, output)
    return output

# window handle로 이미지 위치 및 크기 찾는 함수
def get_win_size(hwnd):
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    return left, top, right, bottom

# 현재 활성화된 창 찾기
def get_active_win():
    return win32gui.GetForegroundWindow()