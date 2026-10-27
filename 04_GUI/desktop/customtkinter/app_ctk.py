import cv2
import dxcam
import numpy as np
import PIL.Image, PIL.ImageTk
import customtkinter
import threading
import json
import os
import time
import serial
import serial.tools.list_ports as sp
import win32gui
import win32com.client
from tkinter import filedialog, messagebox


# 이미지찾기 함수
def find_img(background, target):
    h, w, _ = target.shape
    background = cv2.cvtColor(background, cv2.COLOR_BGR2GRAY)
    target = cv2.cvtColor(target, cv2.COLOR_BGR2GRAY)
    res = cv2.matchTemplate(background, target, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    x, y = max_loc
    return x, y, w, h, max_val

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

def input_test(value):
    msg = "OK"        
    send_key(msg)

# 시리얼로 키입력 보내기.
def send_key(keys):
    key_ary = keys.split(",")
    for key in key_ary:
        if "-" in key:
            t = float(key[1:])
            time.sleep(t)
        else: app.ser.write(keys.encode())
    return


class Slot(customtkinter.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.run = False
        self.in_cool = False
        self.img_path = "미설정"
        temp_img = np.zeros((50,50,3), np.uint8) + 211 #lightgray
        self.roi =temp_img
        self.target = temp_img

        res_lbl = customtkinter.CTkLabel(self, text="인식결과", fg_color="lightgray")
        res_lbl.grid(row=0, column=0, padx=3, pady=3)
        self.lbl_value = customtkinter.CTkLabel(self, text="미확인", fg_color="lightgray")
        self.lbl_value.grid(row=0, column=1, columnspan=2, padx=3, pady=3)

        self.cnv_preview = customtkinter.CTkLabel(self, text="파일선택", width=160, height=50, fg_color="lightgray")
        self.cnv_preview.bind("<ButtonPress-1>", command=lambda _: self.ask_file())
        self.cnv_preview.grid(row=1, column=0, columnspan=2, padx=3, pady=3)

        btn_key = customtkinter.CTkButton(self, text="입력키", width=60, command=lambda: self.ask_text(self.lbl_key))
        btn_key.grid(row=2, column=0, padx=3, pady=3)
        self.lbl_key = customtkinter.CTkLabel(self, text="8", width=100, fg_color="lightgray")
        self.lbl_key.grid(row=2, column=1, padx=3, pady=3)

        btn_cool = customtkinter.CTkButton(self, text="쿨타임", width=60, command=lambda : self.ask_text(self.lbl_cool))
        btn_cool.grid(row=3, column=0, padx=3, pady=3)
        self.lbl_cool = customtkinter.CTkLabel(self, text="30", width=100, fg_color="lightgray")
        self.lbl_cool.grid(row=3, column=1, padx=3, pady=3)

        self.cnv_roi = customtkinter.CTkLabel(self, text="ROI화면", width=160, height=50, fg_color="lightgray")
        self.cnv_roi.grid(row=1, column=2, columnspan=2, padx=3, pady=3)

        btn_roi = customtkinter.CTkButton(self, text="인식영역", width=60, command=lambda: self.ask_text(self.lbl_roi))
        btn_roi.grid(row=2, column=2, padx=3, pady=3)
        self.lbl_roi = customtkinter.CTkLabel(self, text="전체화면", width=100, fg_color="lightgray")
        self.lbl_roi.grid(row=2, column=3, padx=3, pady=3)

        btn_thres = customtkinter.CTkButton(self, text="유사도제한", width=60, command=lambda : self.ask_text(self.lbl_thres))
        btn_thres.cget("font").configure(size=10)
        btn_thres.grid(row=3, column=2, padx=3, pady=3)
        self.lbl_thres = customtkinter.CTkLabel(self, text="0.8", width=100, fg_color="lightgray")
        self.lbl_thres.grid(row=3, column=3, padx=3, pady=3)
        
        self.loop()

    def update_value(self, param):
        self.img_path = param["img_path"]
        self.load_img()
        self.lbl_key.configure(text=param["key"])
        self.lbl_cool.configure(text=param["cool"])
        self.lbl_roi.configure(text=param["roi"])
        self.lbl_thres.configure(text=param["thres"])
        return
    
    def save_value(self):
        param = {}
        param["img_path"] = self.img_path
        param["key"] = self.lbl_key.cget("text")
        param["cool"] = self.lbl_cool.cget("text")
        param["roi"] = self.lbl_roi.cget("text")
        param["thres"] = self.lbl_thres.cget("text")
        return param

    def ask_file(self):
        if self.run == True:
            messagebox.showerror(title="확인", message="실행 중지 후 다시 시도하세요.")
            return
        try:
            self.img_path = filedialog.askopenfile(filetypes=[("Image File", ".jpg .png .jpeg")]).name
            self.load_img()
        except: print("취소했습니다.")
        return
    
    def ask_text(self, widget):
        if self.run == True:
            messagebox.showerror(title="확인", message="실행 중지 후 다시 시도하세요.")
            return
        answer = customtkinter.CTkInputDialog(text="값을 입력하세요.", title="")
        widget.configure(text=answer.get_input())
        return

    def load_img(self):
        if self.img_path == "미설정":
            self.clear_image()
        else:
            try:
                self.target = cv2.imread(self.img_path)
                self.apply_image(self.target, self.cnv_preview)
            except:
                pass
        return

    def clear_image(self):
        gray_img = np.zeros((50,50,3), np.uint8) + 211 #lightgray
        self.apply_image(gray_img, self.cnv_preview, text="파일선택")
        return

    def apply_image(self, img_cv, widget, text="", hide=False):
        if hide == True:
            img_cv = np.zeros((50,50,3), np.uint8) + 211 #lightgray
            img_tk = customtkinter.CTkImage(light_image=PIL.Image.fromarray(img_cv), size=(50, 50))
            widget.configure(image=img_tk, text="숨김")
        else:
            widget_width, widget_height = widget.cget("width"), widget.cget("height")
            img_height, img_width, img_channel = img_cv.shape
            width_ratio = widget_width / img_width
            height_ratio = widget_height / img_height
            ratio = min(width_ratio, height_ratio)
            w, h = int(img_width * ratio) , int(img_height * ratio)
            img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
            img_tk = customtkinter.CTkImage(light_image=PIL.Image.fromarray(img_rgb), size=(w, h))
            widget.configure(image=img_tk, text=text)
        return
    
    def set_roi_img(self, img):
        roi_text = self.lbl_roi.cget("text")
        if roi_text != "전체화면":
            x,y,w,h = map(int, roi_text.split(","))
            img = img[y:y+h,x:x+w]
        self.roi = img
        self.apply_image(img, self.cnv_roi)
        return
    
    def cool_run(self, cooltime):
        self.in_cool = True
        t = threading.Timer(cooltime, self.cool_down)
        t.daemon = True
        t.start()

    def cool_down(self):
        self.in_cool = False
    
    def loop(self):
        if self.run == True:
            # 이미지 찾기
            x, y, w, h, value = find_img(self.target, self.roi)
            self.lbl_value.configure(text=f"유사도:{round(value,2)} x:{x}, y:{y}")

            # 키입력
            key = self.lbl_key.cget("text")
            cooltime = float(self.lbl_cool.cget("text"))
            thres = float(self.lbl_thres.cget("text"))

            if value > thres and self.in_cool == False:
                self.cool_run(cooltime)
                send_key(key)
                
        self.after(500, self.loop)


class Timer(customtkinter.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.run = False
        self.in_cool = False
        
        btn_key = customtkinter.CTkButton(self, text="입력키", width=60, command=lambda: self.ask_text(self.lbl_key))
        btn_key.grid(row=0, column=0, padx=3, pady=3)
        self.lbl_key = customtkinter.CTkLabel(self, text="8", width=100, fg_color="lightgray")
        self.lbl_key.grid(row=0, column=1, padx=3, pady=3)
        
        btn_cool = customtkinter.CTkButton(self, text="쿨타임", width=60, command=lambda: self.ask_text(self.lbl_cool))
        btn_cool.grid(row=0, column=2, padx=3, pady=3)
        self.lbl_cool = customtkinter.CTkLabel(self, text="2", width=100, fg_color="lightgray")
        self.lbl_cool.grid(row=0, column=3, padx=3, pady=3)

        self.loop()

    def update_value(self, param):
        self.lbl_key.configure(text=param["key"])
        self.lbl_cool.configure(text=param["cool"])
        return

    def save_value(self):
        param = {}
        param["key"] = self.lbl_key.cget("text")
        param["cool"] = self.lbl_cool.cget("text")
        return param

    def ask_text(self, widget):
        if self.run == True:
            messagebox.showerror(title="확인", message="기능을 중지시킨 후 다시 시도하세요.")
            return
        answer = customtkinter.CTkInputDialog(text="값을 입력하세요.", title="")
        widget.configure(text=answer.get_input())
        return
    
    def cool_run(self, cooltime):
        self.in_cool = True
        t = threading.Timer(cooltime, self.cool_down)
        t.daemon = True
        t.start()

    def cool_down(self):
        self.in_cool = False
    
    def loop(self):
        if self.run == True:
            key = self.lbl_key.cget("text")
            cooltime = float(self.lbl_cool.cget("text"))
            if self.in_cool == False:
                self.cool_run(cooltime)
                send_key(key)
        self.after(200, self.loop)


class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title("Game Pathfinder")
        self.geometry("+1490+0")
        
        self.arduino_connect = False
        
        self.camera = dxcam.create(output_color="BGR")
        self.camera.start(target_fps=2)

        # 캡처화면, 아두이노, 윈도우정보, 설정관리
        frame_main = customtkinter.CTkTabview(self, width=100, height=100)
        frame_main.grid(row=0, column=0, padx=3, pady=3)
        monitor_tab = frame_main.add("캡처화면")
        self.cnv_monitor = customtkinter.CTkLabel(monitor_tab, text="", width=350, height=180)
        self.cnv_monitor.grid(row=0, column=0, padx=3, pady=3)

        arduino_tab = frame_main.add("아두이노")
        self.combo_arduino = customtkinter.CTkComboBox(arduino_tab, values=["연결할 기기를 선택하세요"], width=240, command=self.connect_arduino)
        self.combo_arduino.grid(row=0, column=0, padx=3, pady=3)
        btn_refresh = customtkinter.CTkButton(arduino_tab, text="새로고침", width=100, command=self.port_refresh)
        btn_refresh.grid(row=0, column=1, padx=3, pady=3)
        test_field = customtkinter.CTkEntry(arduino_tab, placeholder_text="여기를 클릭하면 테스트문자를 입력합니다.", width=350)
        test_field.bind("<ButtonPress-1>", command=input_test)
        test_field.grid(row=1, column=0, columnspan=2, padx=3, pady=3)

        window_info_tab = frame_main.add("윈도우 정보")
        self.win_ary = get_win_list()
        win_title_ary = [t[0] for t in self.win_ary]
        self.combo_hwnd = customtkinter.CTkComboBox(window_info_tab, values=win_title_ary, width=240)
        self.combo_hwnd.grid(row=0, column=0, padx=3, pady=3)
        btn_move_win = customtkinter.CTkButton(window_info_tab, text="새로고침", width=100, command=self.window_refresh)
        btn_move_win.grid(row=0, column=1, padx=3, pady=3)
        self.lbl_win_info = customtkinter.CTkTextbox(window_info_tab, width=350, height=130)
        self.lbl_win_info.grid(row=1, column=0, columnspan=2, pady=3)

        setting_tab = frame_main.add("기타")
        btn_save = customtkinter.CTkButton(setting_tab, text="설정 저장", width=350, command=self.save_settings)
        btn_save.grid(row=0, column=0, padx=3, pady=3)
        btn_init = customtkinter.CTkButton(setting_tab, text="설정 초기화", width=350, command=self.init_settings)
        btn_init.grid(row=1, column=0, padx=3, pady=3)
        btn_help = customtkinter.CTkButton(setting_tab, text="도움말", width=350)
        btn_help.grid(row=2, column=0, padx=3, pady=3)

        # 타이머 UI
        frame_timer = customtkinter.CTkTabview(self, width=100, height=100)
        frame_timer.grid(row=2, column=0, padx=3, pady=3)
        tab_timer1 = frame_timer.add("타이머1")
        tab_timer2 = frame_timer.add("타이머2")
        tab_timer3 = frame_timer.add("타이머3")
        tab_timer4 = frame_timer.add("타이머4")
        tab_timer5 = frame_timer.add("타이머5")
        self.timer1 = Timer(tab_timer1, border_width=1)
        self.timer2 = Timer(tab_timer2, border_width=1)
        self.timer3 = Timer(tab_timer3, border_width=1)
        self.timer4 = Timer(tab_timer4, border_width=1)
        self.timer5 = Timer(tab_timer5, border_width=1)
        self.timer_ary = [self.timer1, self.timer2, self.timer3, self.timer4, self.timer5]
        self.timer_cooltime_ary = []
        for idx, timer in enumerate(self.timer_ary):
            timer.grid(row=idx, column=0, padx=3, pady=3)
            self.timer_cooltime_ary.append(False)


        # 슬롯 UI
        frame_slot = customtkinter.CTkTabview(self, width=100, height=50)
        frame_slot.grid(row=3, column=0, padx=3, pady=3)
        tab_slot1 = frame_slot.add("슬롯1")
        tab_slot2 = frame_slot.add("슬롯2")
        tab_slot3 = frame_slot.add("슬롯3")
        tab_slot4 = frame_slot.add("슬롯4")
        tab_slot5 = frame_slot.add("슬롯5")
        self.slot1 = Slot(tab_slot1, border_width=1)
        self.slot2 = Slot(tab_slot2, border_width=1)
        self.slot3 = Slot(tab_slot3, border_width=1)
        self.slot4 = Slot(tab_slot4, border_width=1)
        self.slot5 = Slot(tab_slot5, border_width=1)
        self.slot_ary = [self.slot1, self.slot2, self.slot3, self.slot4, self.slot5]        
        self.slot_cooltime_ary = []
        for idx, slot in enumerate(self.slot_ary):
            slot.grid(row=idx, column=0, padx=3, pady=3)
            self.slot_cooltime_ary.append(False)


        # 토글 UI
        frame_run = customtkinter.CTkTabview(self, height=100)
        frame_run.grid(row=4, column=0, padx=3, pady=3)
        tab_run = frame_run.add("실행관리")
        self.run_timer1 = self.ToggleButton(tab_run, "타이머1")
        self.run_timer2 = self.ToggleButton(tab_run, "타이머2")
        self.run_timer3 = self.ToggleButton(tab_run, "타이머3")
        self.run_timer4 = self.ToggleButton(tab_run, "타이머4")
        self.run_timer5 = self.ToggleButton(tab_run, "타이머5")
        self.run_timer_ary = [self.run_timer1, self.run_timer2, self.run_timer3, self.run_timer4,self.run_timer5]
        for idx, timer in enumerate(self.run_timer_ary):
            timer.grid(row=0, column=idx, padx=3, pady=3)
        
        self.run_slot1 = self.ToggleButton(tab_run, "슬롯1")
        self.run_slot2 = self.ToggleButton(tab_run, "슬롯2")
        self.run_slot3 = self.ToggleButton(tab_run, "슬롯3")
        self.run_slot4 = self.ToggleButton(tab_run, "슬롯4")
        self.run_slot5 = self.ToggleButton(tab_run, "슬롯5")
        self.slot_run_ary = [self.run_slot1, self.run_slot2, self.run_slot3, self.run_slot4,self.run_slot5]
        for idx, slot in enumerate(self.slot_run_ary):
            slot.grid(row=1, column=idx, padx=3, pady=3)      

        self.default_param = {
            "timer1": {"key": "f", "cool": "0.2"},
            "timer2": {"key": "1", "cool": "2"},
            "timer3": {"key": "2", "cool": "2"},
            "timer4": {"key": "3", "cool": "2"},
            "timer5": {"key": "4", "cool": "2"},
            "slot1": {"img_path": "미설정", "key": "1", "cool": "5", "roi": "전체화면", "thres": "0.8"},
            "slot2": {"img_path": "미설정", "key": "2", "cool": "5", "roi": "전체화면", "thres": "0.8"},
            "slot3": {"img_path": "미설정", "key": "3", "cool": "5", "roi": "전체화면", "thres": "0.8"},
            "slot4": {"img_path": "미설정", "key": "4", "cool": "5", "roi": "전체화면", "thres": "0.8"},
            "slot5": {"img_path": "미설정", "key": "5", "cool": "5", "roi": "전체화면", "thres": "0.8"},
        }
        param = self.load_data("userdata.json") if os.path.isfile("userdata.json") else self.default_param        
        self.update_settings(param)

        self.port_refresh()
        self.window_info()
        self.update_frame()

    def ToggleButton(self, master, text):
        btn = customtkinter.CTkButton(master, text=text, width=65, fg_color="gray", hover_color="gray", command=lambda: self.toggle_event(btn))
        btn.state = False
        return btn

    def toggle_event(self, button):
        button.state = not button.state
        button_text = button.cget("text")
        button_num = int(button_text[-1])
        button_idx = button_num - 1
        
        if self.arduino_connect == False and button.state == True:
            messagebox.showerror(title="확인", message="아두이노 연결 후 다시 시도하세요.")
            return

        if "타이머" in button_text: #타이머
            self.timer_ary[button_idx].run = button.state
            color = "#3b8ed0" if button.state == True else "gray"
            button.configure(fg_color=color, hover_color=color)
        
        else: # 슬롯
            self.slot_ary[button_idx].run = button.state
            color = "#3b8ed0" if button.state == True else "gray"
            button.configure(fg_color=color, hover_color=color)
        return

    def save_settings(self):
        param = {}
        for idx, timer in enumerate(self.timer_ary):
            param[f"timer{idx+1}"] = timer.save_value()      
        for idx, slot in enumerate(self.slot_ary):
            param[f"slot{idx+1}"] = slot.save_value()
        with open("userdata.json", "w") as file:
            json.dump(param, file, indent=4)
            print("현재 설정을 userdata.json 파일로 저장했습니다.")

    def update_settings(self, param):
        for idx, timer in enumerate(self.timer_ary):
            timer.update_value(param[f"timer{idx+1}"])
        for idx, slot in enumerate(self.slot_ary):
            slot.update_value(param[f"slot{idx+1}"])

    def init_settings(self):
        self.update_settings(self.default_param)

    def load_data(self, filename="userdata.json"):
        with open(filename, "r") as file:
            return json.load(file)

    def find_port(self):
        res = []
        for port, desc, hwid in sorted(sp.comports()):
            res.append(f"{port}, {desc}")
        return res
    
    def port_refresh(self):
        ports = self.find_port()
        self.combo_arduino.configure(values=ports)

    def connect_arduino(self, value):
        try:
            port = value.split(",")[0]
            self.ser = serial.Serial(port=port, baudrate=9600)
            print(f"{value}으로 시리얼이 연결되었습니다.")
            self.arduino_connect = True
        except: print("연결에 실패했습니다.")

    def window_refresh(self):
        self.win_ary = get_win_list()
        win_title_ary = [t[0] for t in self.win_ary]
        self.combo_hwnd.configure(values=win_title_ary)

    def window_info(self):
        active_hwnd = win32gui.GetForegroundWindow()
        self.active_title = win32gui.GetWindowText(active_hwnd)
        self.selected_title = self.combo_hwnd.get()
        self.selected_hwnd = [x[1] for x in self.win_ary if x[0] == self.selected_title][0]
        left, top, right, bottom = win32gui.GetWindowRect(self.selected_hwnd)
        x, y, w, h = left, top, right-left, bottom-top
        data_str = f"실행중인 윈도우 : {self.active_title}\n"
        data_str += f"선택한 윈도우 : {self.selected_title}\n"
        data_str += f"  - X위치 : {x}\n"
        data_str += f"  - Y위치 : {y}\n"
        data_str += f"  - 폭 : {w}\n"
        data_str += f"  - 높이 : {h}\n"
        
        self.lbl_win_info.delete("0.0", "end")
        self.lbl_win_info.insert("0.0", data_str)
        self.after(1000, self.window_info)

    def make_thumbnail(self, img):
        widget_width, widget_height = self.cnv_monitor.cget("width"), self.cnv_monitor.cget("height")
        img_height, img_width, img_channel = img.shape
        width_ratio = widget_width / img_width
        height_ratio = widget_height / img_height
        ratio = min(width_ratio, height_ratio)
        w, h = int(img_width * ratio) , int(img_height * ratio)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_tk = customtkinter.CTkImage(light_image=PIL.Image.fromarray(img_rgb), size=(w, h))
        self.cnv_monitor.configure(image=img_tk)

    def update_frame(self):
        self.frame = self.camera.get_latest_frame()
        # 썸네일 업데이트
        self.make_thumbnail(self.frame)
        
        # 실행중인 슬롯에 이미지 보내기
        for idx, slot in enumerate(self.slot_run_ary):
            if slot.state == True:
                self.slot_ary[idx].set_roi_img(self.frame)
        
        self.after(500, self.update_frame)


app = App()
app.mainloop()