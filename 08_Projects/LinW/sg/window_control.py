import win32gui, win32com.client

shell = win32com.client.Dispatch("WScript.Shell")


def set_foreground(hwnd):
    shell.SendKeys('%')    
    win32gui.SetForegroundWindow(hwnd)
    return True

def get_win_size(hwnd):
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    return left, top, right, bottom

def get_lin_window(name):
    window_text = "리니지W l " + name
    window_handle = win32gui.FindWindow(None, window_text)
    return window_handle