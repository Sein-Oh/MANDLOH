import customtkinter
import PIL.Image, PIL.ImageTk
import cv2
import numpy as np
import dxcam
import win32gui

data = {
    "timerslot" : {
        "slot1" : {
            "name" : "테스트1",
            "key" : "1",
            "cooltime" : "3"
        },
        "slot2" : {
            "name" : "테스트2",
            "key" : "2",
            "cooltime" : "3"
        },
        "slot3" : {
            "name" : "테스트3",
            "key" : "3",
            "cooltime" : "3"
        },
        "slot4" : {
            "name" : "테스트4",
            "key" : "4",
            "cooltime" : "3"
        }
    },
    "hpslot" : {
        "x1" : "0",
        "y1" : "0",
        "x2" : "1920",
        "y2" : "1080",
        "threshold" : "210",
        "slot1" : {
            "name" : "테스트1",
            "key" : "1",
            "cooltime" : "3",
            "minhp" : "0",
            "maxhp" : "100"
        },
        "slot2" : {
            "name" : "테스트2",
            "key" : "2",
            "cooltime" : "3",
            "minhp" : "0",
            "maxhp" : "100"
        },
        "slot3" : {
            "name" : "테스트3",
            "key" : "3",
            "cooltime" : "3",
            "minhp" : "0",
            "maxhp" : "100"
        },
        "slot4" : {
            "name" : "테스트4",
            "key" : "4",
            "cooltime" : "3",
            "minhp" : "0",
            "maxhp" : "100"
        }
    },
    "imgslot" : {
        "slot1" : {},
        "slot2" : {},
        "slot3" : {},
        "slot4" : {}
    }
}

class TimerSetting(customtkinter.CTkToplevel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("타이머 설정")
        self.geometry("850x210+400+200")

        self.frame1 = customtkinter.CTkFrame(self)
        self.frame1.place(x=0, y=0)
        customtkinter.CTkLabel(self.frame1, text="슬롯1", width=190, height=30, fg_color="gray", corner_radius=6).grid(row=0, column=0, columnspan=2, padx=5, pady=5)
        customtkinter.CTkLabel(self.frame1, text="슬롯명", width=90, height=30).grid(row=1, column=0, padx=5, pady=5)
        self.slot1_name = customtkinter.CTkEntry(self.frame1, width=100, height=30)
        self.slot1_name.grid(row=1, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame1, text="입력키", width=90, height=30).grid(row=2, column=0, padx=5, pady=5)
        self.slot1_key = customtkinter.CTkEntry(self.frame1, width=100, height=30)
        self.slot1_key.grid(row=2, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame1, text="쿨타임", width=90, height=30).grid(row=3, column=0, padx=5, pady=5)
        self.slot1_cooltime = customtkinter.CTkEntry(self.frame1, width=100, height=30)
        self.slot1_cooltime.grid(row=3, column=1, padx=5, pady=5)

        self.frame2 = customtkinter.CTkFrame(self)
        self.frame2.place(x=220, y=0)
        customtkinter.CTkLabel(self.frame2, text="슬롯2", width=190, height=30, fg_color="gray", corner_radius=6).grid(row=0, column=0, columnspan=2, padx=5, pady=5)
        customtkinter.CTkLabel(self.frame2, text="슬롯명", width=90, height=30).grid(row=1, column=0, padx=5, pady=5)
        self.slot2_name = customtkinter.CTkEntry(self.frame2, width=100, height=30)
        self.slot2_name.grid(row=1, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame2, text="입력키", width=90, height=30).grid(row=2, column=0, padx=5, pady=5)
        self.slot2_key = customtkinter.CTkEntry(self.frame2, width=100, height=30)
        self.slot2_key.grid(row=2, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame2, text="쿨타임", width=90, height=30).grid(row=3, column=0, padx=5, pady=5)
        self.slot2_cooltime = customtkinter.CTkEntry(self.frame2, width=100, height=30)
        self.slot2_cooltime.grid(row=3, column=1, padx=5, pady=5)

        self.frame3 = customtkinter.CTkFrame(self)
        self.frame3.place(x=430, y=0)
        customtkinter.CTkLabel(self.frame3, text="슬롯3", width=190, height=30, fg_color="gray", corner_radius=6).grid(row=0, column=0, columnspan=2, padx=5, pady=5)
        customtkinter.CTkLabel(self.frame3, text="슬롯명", width=90, height=30).grid(row=1, column=0, padx=5, pady=5)
        self.slot3_name = customtkinter.CTkEntry(self.frame3, width=100, height=30)
        self.slot3_name.grid(row=1, column=1, padx=5, pady=5)
        
        customtkinter.CTkLabel(self.frame3, text="입력키", width=90, height=30).grid(row=2, column=0, padx=5, pady=5)
        self.slot3_key = customtkinter.CTkEntry(self.frame3, width=100, height=30)
        self.slot3_key.grid(row=2, column=1, padx=5, pady=5)
        
        customtkinter.CTkLabel(self.frame3, text="쿨타임", width=90, height=30).grid(row=3, column=0, padx=5, pady=5)
        self.slot3_cooltime = customtkinter.CTkEntry(self.frame3, width=100, height=30)
        self.slot3_cooltime.grid(row=3, column=1, padx=5, pady=5)

        self.frame4 = customtkinter.CTkFrame(self)
        self.frame4.place(x=640, y=0)
        customtkinter.CTkLabel(self.frame4, text="슬롯4", width=190, height=30, fg_color="gray", corner_radius=6).grid(row=0, column=0, columnspan=2, padx=5, pady=5)
        customtkinter.CTkLabel(self.frame4, text="슬롯명", width=90, height=30).grid(row=1, column=0, padx=5, pady=5)
        self.slot4_name = customtkinter.CTkEntry(self.frame4, width=100, height=30)
        self.slot4_name.grid(row=1, column=1, padx=5, pady=5)
        
        customtkinter.CTkLabel(self.frame4, text="입력키", width=90, height=30).grid(row=2, column=0, padx=5, pady=5)
        self.slot4_key = customtkinter.CTkEntry(self.frame4, width=100, height=30)
        self.slot4_key.grid(row=2, column=1, padx=5, pady=5)
        
        customtkinter.CTkLabel(self.frame4, text="쿨타임", width=90, height=30).grid(row=3, column=0, padx=5, pady=5)
        self.slot4_cooltime = customtkinter.CTkEntry(self.frame4, width=100, height=30)
        self.slot4_cooltime.grid(row=3, column=1, padx=5, pady=5)

        customtkinter.CTkButton(self, text="저장", width=100, height=30, command=self.save).place(x=10, y=170)

    def save(self):
        data["timerslot"]["slot1"]["name"] = self.slot1_name.get()
        data["timerslot"]["slot1"]["key"] = self.slot1_key.get()
        data["timerslot"]["slot1"]["cooltime"] = self.slot1_cooltime.get()
        data["timerslot"]["slot2"]["name"] = self.slot2_name.get()
        data["timerslot"]["slot2"]["key"] = self.slot2_key.get()
        data["timerslot"]["slot2"]["cooltime"] = self.slot2_cooltime.get()
        data["timerslot"]["slot3"]["name"] = self.slot3_name.get()
        data["timerslot"]["slot3"]["key"] = self.slot3_key.get()
        data["timerslot"]["slot3"]["cooltime"] = self.slot3_cooltime.get()
        data["timerslot"]["slot4"]["name"] = self.slot4_name.get()
        data["timerslot"]["slot4"]["key"] = self.slot4_key.get()
        data["timerslot"]["slot4"]["cooltime"] = self.slot4_cooltime.get()
        print(data["timerslot"])
        app.apply()


    def clear_data(self):
        self.slot1_name.delete(0, 99)
        self.slot1_key.delete(0, 99)
        self.slot1_cooltime.delete(0, 99)
        self.slot2_name.delete(0, 99)
        self.slot2_key.delete(0, 99)
        self.slot2_cooltime.delete(0, 99)
        self.slot3_name.delete(0, 99)
        self.slot3_key.delete(0, 99)
        self.slot3_cooltime.delete(0, 99)
        self.slot4_name.delete(0, 99)
        self.slot4_key.delete(0, 99)
        self.slot4_cooltime.delete(0, 99)

    def apply_data(self):
        self.clear_data()
        self.slot1_name.insert(0, data["timerslot"]["slot1"]["name"])
        self.slot1_key.insert(0, data["timerslot"]["slot1"]["key"])
        self.slot1_cooltime.insert(0, data["timerslot"]["slot1"]["cooltime"])
        self.slot2_name.insert(0, data["timerslot"]["slot2"]["name"])
        self.slot2_key.insert(0, data["timerslot"]["slot2"]["key"])
        self.slot2_cooltime.insert(0, data["timerslot"]["slot2"]["cooltime"])
        self.slot3_name.insert(0, data["timerslot"]["slot3"]["name"])
        self.slot3_key.insert(0, data["timerslot"]["slot3"]["key"])
        self.slot3_cooltime.insert(0, data["timerslot"]["slot3"]["cooltime"])
        self.slot4_name.insert(0, data["timerslot"]["slot4"]["name"])
        self.slot4_key.insert(0, data["timerslot"]["slot4"]["key"])
        self.slot4_cooltime.insert(0, data["timerslot"]["slot4"]["cooltime"])


class HpslotSetting(customtkinter.CTkToplevel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("HP슬롯 설정")
        self.geometry("1060x290+500+300")

        self.frame = customtkinter.CTkFrame(self)
        self.frame.place(x=0, y=0)
        customtkinter.CTkLabel(self.frame, text="필수설정", width=190, height=30, fg_color="gray", corner_radius=6).grid(row=0, column=0, columnspan=2, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame, text="캡처 x1", width=90, height=30).grid(row=1, column=0, padx=5, pady=5)
        self.x1 = customtkinter.CTkEntry(self.frame, width=100, height=30)
        self.x1.grid(row=1, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame, text="캡처 y1", width=90, height=30).grid(row=2, column=0, padx=5, pady=5)
        self.y1 = customtkinter.CTkEntry(self.frame, width=100, height=30)
        self.y1.grid(row=2, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame, text="캡처 x2", width=90, height=30).grid(row=3, column=0, padx=5, pady=5)
        self.x2 = customtkinter.CTkEntry(self.frame, width=100, height=30)
        self.x2.grid(row=3, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame, text="캡처 y2", width=90, height=30).grid(row=4, column=0, padx=5, pady=5)
        self.y2 = customtkinter.CTkEntry(self.frame, width=100, height=30)
        self.y2.grid(row=4, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame, text="Threshold", width=90, height=30).grid(row=5, column=0, padx=5, pady=5)
        self.threshold = customtkinter.CTkEntry(self.frame, width=100, height=30)
        self.threshold.grid(row=5, column=1, padx=5, pady=5)

        self.frame1 = customtkinter.CTkFrame(self)
        self.frame1.place(x=220, y=0)

        customtkinter.CTkLabel(self.frame1, text="슬롯1", width=190, height=30, fg_color="gray", corner_radius=6).grid(row=0, column=0, columnspan=2, padx=5, pady=5)
        customtkinter.CTkLabel(self.frame1, text="슬롯명", width=90, height=30).grid(row=1, column=0, padx=5, pady=5)
        self.slot1_name = customtkinter.CTkEntry(self.frame1, width=100, height=30)
        self.slot1_name.grid(row=1, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame1, text="입력키", width=90, height=30).grid(row=2, column=0, padx=5, pady=5)
        self.slot1_key = customtkinter.CTkEntry(self.frame1, width=100, height=30)
        self.slot1_key.grid(row=2, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame1, text="쿨타임", width=90, height=30).grid(row=3, column=0, padx=5, pady=5)
        self.slot1_cooltime = customtkinter.CTkEntry(self.frame1, width=100, height=30)
        self.slot1_cooltime.grid(row=3, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame1, text="최소HP", width=90, height=30).grid(row=4, column=0, padx=5, pady=5)
        self.slot1_minhp = customtkinter.CTkEntry(self.frame1, width=100, height=30)
        self.slot1_minhp.grid(row=4, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame1, text="최대HP", width=90, height=30).grid(row=5, column=0, padx=5, pady=5)
        self.slot1_maxhp = customtkinter.CTkEntry(self.frame1, width=100, height=30)
        self.slot1_maxhp.grid(row=5, column=1, padx=5, pady=5)

        self.frame2 = customtkinter.CTkFrame(self)
        self.frame2.place(x=430, y=0)

        customtkinter.CTkLabel(self.frame2, text="슬롯2", width=190, height=30, fg_color="gray", corner_radius=6).grid(row=0, column=0, columnspan=2, padx=5, pady=5)
        customtkinter.CTkLabel(self.frame2, text="슬롯명", width=90, height=30).grid(row=1, column=0, padx=5, pady=5)
        self.slot2_name = customtkinter.CTkEntry(self.frame2, width=100, height=30)
        self.slot2_name.grid(row=1, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame2, text="입력키", width=90, height=30).grid(row=2, column=0, padx=5, pady=5)
        self.slot2_key = customtkinter.CTkEntry(self.frame2, width=100, height=30)
        self.slot2_key.grid(row=2, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame2, text="쿨타임", width=90, height=30).grid(row=3, column=0, padx=5, pady=5)
        self.slot2_cooltime = customtkinter.CTkEntry(self.frame2, width=100, height=30)
        self.slot2_cooltime.grid(row=3, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame2, text="최소HP", width=90, height=30).grid(row=4, column=0, padx=5, pady=5)
        self.slot2_minhp = customtkinter.CTkEntry(self.frame2, width=100, height=30)
        self.slot2_minhp.grid(row=4, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame2, text="최대HP", width=90, height=30).grid(row=5, column=0, padx=5, pady=5)
        self.slot2_maxhp = customtkinter.CTkEntry(self.frame2, width=100, height=30)
        self.slot2_maxhp.grid(row=5, column=1, padx=5, pady=5)

        self.frame3 = customtkinter.CTkFrame(self)
        self.frame3.place(x=640, y=0)

        customtkinter.CTkLabel(self.frame3, text="슬롯3", width=190, height=30, fg_color="gray", corner_radius=6).grid(row=0, column=0, columnspan=2, padx=5, pady=5)
        customtkinter.CTkLabel(self.frame3, text="슬롯명", width=90, height=30).grid(row=1, column=0, padx=5, pady=5)
        self.slot3_name = customtkinter.CTkEntry(self.frame3, width=100, height=30)
        self.slot3_name.grid(row=1, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame3, text="입력키", width=90, height=30).grid(row=2, column=0, padx=5, pady=5)
        self.slot3_key = customtkinter.CTkEntry(self.frame3, width=100, height=30)
        self.slot3_key.grid(row=2, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame3, text="쿨타임", width=90, height=30).grid(row=3, column=0, padx=5, pady=5)
        self.slot3_cooltime = customtkinter.CTkEntry(self.frame3, width=100, height=30)
        self.slot3_cooltime.grid(row=3, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame3, text="최소HP", width=90, height=30).grid(row=4, column=0, padx=5, pady=5)
        self.slot3_minhp = customtkinter.CTkEntry(self.frame3, width=100, height=30)
        self.slot3_minhp.grid(row=4, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame3, text="최대HP", width=90, height=30).grid(row=5, column=0, padx=5, pady=5)
        self.slot3_maxhp = customtkinter.CTkEntry(self.frame3, width=100, height=30)
        self.slot3_maxhp.grid(row=5, column=1, padx=5, pady=5)

        self.frame4 = customtkinter.CTkFrame(self)
        self.frame4.place(x=850, y=0)

        customtkinter.CTkLabel(self.frame4, text="슬롯4", width=190, height=30, fg_color="gray", corner_radius=6).grid(row=0, column=0, columnspan=2, padx=5, pady=5)
        customtkinter.CTkLabel(self.frame4, text="슬롯명", width=90, height=30).grid(row=1, column=0, padx=5, pady=5)
        self.slot4_name = customtkinter.CTkEntry(self.frame4, width=100, height=30)
        self.slot4_name.grid(row=1, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame4, text="입력키", width=90, height=30).grid(row=2, column=0, padx=5, pady=5)
        self.slot4_key = customtkinter.CTkEntry(self.frame4, width=100, height=30)
        self.slot4_key.grid(row=2, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame4, text="쿨타임", width=90, height=30).grid(row=3, column=0, padx=5, pady=5)
        self.slot4_cooltime = customtkinter.CTkEntry(self.frame4, width=100, height=30)
        self.slot4_cooltime.grid(row=3, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame4, text="최소HP", width=90, height=30).grid(row=4, column=0, padx=5, pady=5)
        self.slot4_minhp = customtkinter.CTkEntry(self.frame4, width=100, height=30)
        self.slot4_minhp.grid(row=4, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame4, text="최대HP", width=90, height=30).grid(row=5, column=0, padx=5, pady=5)
        self.slot4_maxhp = customtkinter.CTkEntry(self.frame4, width=100, height=30)
        self.slot4_maxhp.grid(row=5, column=1, padx=5, pady=5)

        customtkinter.CTkButton(self, text="저장", width=100, height=30, command=self.save).place(x=10, y=250)

    def save(self):
        data["hpslot"]["x1"] = self.x1.get()
        data["hpslot"]["y1"] = self.y1.get()
        data["hpslot"]["x2"] = self.x2.get()
        data["hpslot"]["y2"] = self.y2.get()
        data["hpslot"]["threshold"] = self.threshold.get()

        data["hpslot"]["slot1"]["name"] = self.slot1_name.get()
        data["hpslot"]["slot1"]["key"] = self.slot1_key.get()
        data["hpslot"]["slot1"]["cooltime"] = self.slot1_cooltime.get()
        data["hpslot"]["slot1"]["minhp"] = self.slot1_minhp.get()
        data["hpslot"]["slot1"]["maxhp"] = self.slot1_maxhp.get()

        data["hpslot"]["slot2"]["name"] = self.slot2_name.get()
        data["hpslot"]["slot2"]["key"] = self.slot2_key.get()
        data["hpslot"]["slot2"]["cooltime"] = self.slot2_cooltime.get()
        data["hpslot"]["slot2"]["minhp"] = self.slot2_minhp.get()
        data["hpslot"]["slot2"]["maxhp"] = self.slot2_maxhp.get()

        data["hpslot"]["slot3"]["name"] = self.slot3_name.get()
        data["hpslot"]["slot3"]["key"] = self.slot3_key.get()
        data["hpslot"]["slot3"]["cooltime"] = self.slot3_cooltime.get()
        data["hpslot"]["slot3"]["minhp"] = self.slot3_minhp.get()
        data["hpslot"]["slot3"]["maxhp"] = self.slot3_maxhp.get()

        data["hpslot"]["slot4"]["name"] = self.slot4_name.get()
        data["hpslot"]["slot4"]["key"] = self.slot4_key.get()
        data["hpslot"]["slot4"]["cooltime"] = self.slot4_cooltime.get()
        data["hpslot"]["slot4"]["minhp"] = self.slot4_minhp.get()
        data["hpslot"]["slot4"]["maxhp"] = self.slot4_maxhp.get()
        print(data["hpslot"])
        app.apply()

    def clear_data(self):
        self.x1.delete(0, 99)
        self.y1.delete(0, 99)
        self.x2.delete(0, 99)
        self.y2.delete(0, 99)
        self.threshold.delete(0, 99)

        self.slot1_name.delete(0, 99)
        self.slot1_key.delete(0, 99)
        self.slot1_cooltime.delete(0, 99)
        self.slot1_minhp.delete(0, 99)
        self.slot1_maxhp.delete(0, 99)

        self.slot2_name.delete(0, 99)
        self.slot2_key.delete(0, 99)
        self.slot2_cooltime.delete(0, 99)
        self.slot2_minhp.delete(0, 99)
        self.slot2_maxhp.delete(0, 99)

        self.slot3_name.delete(0, 99)
        self.slot3_key.delete(0, 99)
        self.slot3_cooltime.delete(0, 99)
        self.slot3_minhp.delete(0, 99)
        self.slot3_maxhp.delete(0, 99)

        self.slot4_name.delete(0, 99)
        self.slot4_key.delete(0, 99)
        self.slot4_cooltime.delete(0, 99)
        self.slot4_minhp.delete(0, 99)
        self.slot4_maxhp.delete(0, 99)

    def apply_data(self):
        self.clear_data()
        self.x1.insert(0, data["hpslot"]["x1"])
        self.y1.insert(0, data["hpslot"]["y1"])
        self.x2.insert(0, data["hpslot"]["x2"])
        self.y2.insert(0, data["hpslot"]["y2"])
        self.threshold.insert(0, data["hpslot"]["threshold"])

        self.slot1_name.insert(0, data["hpslot"]["slot1"]["name"])
        self.slot1_key.insert(0, data["hpslot"]["slot1"]["key"])
        self.slot1_cooltime.insert(0, data["hpslot"]["slot1"]["cooltime"])
        self.slot1_minhp.insert(0, data["hpslot"]["slot1"]["minhp"])
        self.slot1_maxhp.insert(0, data["hpslot"]["slot1"]["maxhp"])

        self.slot2_name.insert(0, data["hpslot"]["slot2"]["name"])
        self.slot2_key.insert(0, data["hpslot"]["slot2"]["key"])
        self.slot2_cooltime.insert(0, data["hpslot"]["slot2"]["cooltime"])
        self.slot2_minhp.insert(0, data["hpslot"]["slot2"]["minhp"])
        self.slot2_maxhp.insert(0, data["hpslot"]["slot2"]["maxhp"])

        self.slot3_name.insert(0, data["hpslot"]["slot3"]["name"])
        self.slot3_key.insert(0, data["hpslot"]["slot3"]["key"])
        self.slot3_cooltime.insert(0, data["hpslot"]["slot3"]["cooltime"])
        self.slot3_minhp.insert(0, data["hpslot"]["slot3"]["minhp"])
        self.slot3_maxhp.insert(0, data["hpslot"]["slot3"]["maxhp"])

        self.slot4_name.insert(0, data["hpslot"]["slot4"]["name"])
        self.slot4_key.insert(0, data["hpslot"]["slot4"]["key"])
        self.slot4_cooltime.insert(0, data["hpslot"]["slot4"]["cooltime"])
        self.slot4_minhp.insert(0, data["hpslot"]["slot4"]["minhp"])
        self.slot4_maxhp.insert(0, data["hpslot"]["slot4"]["maxhp"])


class IMGslotSetting(customtkinter.CTkToplevel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("IMG슬롯 설정")
        self.geometry("850x520+600+400")

        self.frame1 = customtkinter.CTkFrame(self)
        self.frame1.place(x=0, y=0)

        customtkinter.CTkLabel(self.frame1, text="슬롯1", width=190, height=30, fg_color="gray", corner_radius=6).grid(row=0, column=0, columnspan=2, padx=5, pady=5)
        customtkinter.CTkLabel(self.frame1, text="슬롯명", width=90, height=30).grid(row=1, column=0, padx=5, pady=5)
        self.slot1_name = customtkinter.CTkEntry(self.frame1, width=100, height=30)
        self.slot1_name.grid(row=1, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame1, text="입력키", width=90, height=30).grid(row=2, column=0, padx=5, pady=5)
        self.slot1_key = customtkinter.CTkEntry(self.frame1, width=100, height=30)
        self.slot1_key.grid(row=2, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame1, text="쿨타임", width=90, height=30).grid(row=3, column=0, padx=5, pady=5)
        self.slot1_cooltime = customtkinter.CTkEntry(self.frame1, width=100, height=30)
        self.slot1_cooltime.grid(row=3, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame1, text="Threshold", width=90, height=30).grid(row=4, column=0, padx=5, pady=5)
        self.slot1_threshold = customtkinter.CTkEntry(self.frame1, width=100, height=30)
        self.slot1_threshold.grid(row=4, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame1, text="캡처 x1", width=90, height=30).grid(row=5, column=0, padx=5, pady=5)
        self.slot1_x1 = customtkinter.CTkEntry(self.frame1, width=100, height=30)
        self.slot1_x1.grid(row=5, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame1, text="캡처 y1", width=90, height=30).grid(row=6, column=0, padx=5, pady=5)
        self.slot1_y1 = customtkinter.CTkEntry(self.frame1, width=100, height=30)
        self.slot1_y1.grid(row=6, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame1, text="캡처 x2", width=90, height=30).grid(row=7, column=0, padx=5, pady=5)
        self.slot1_x2 = customtkinter.CTkEntry(self.frame1, width=100, height=30)
        self.slot1_x2.grid(row=7, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame1, text="캡처 y2", width=90, height=30).grid(row=8, column=0, padx=5, pady=5)
        self.slot1_y2 = customtkinter.CTkEntry(self.frame1, width=100, height=30)
        self.slot1_y2.grid(row=8, column=1, padx=5, pady=5)

        self.slot1_target_btn = customtkinter.CTkButton(self.frame1, text="대상 이미지", width=90, height=30, command=lambda: self.load_img(self.slot1_canvas))
        self.slot1_target_btn.grid(row=9, column=0, padx=5, pady=5)
        self.slot1_canvas = customtkinter.CTkLabel(self.frame1, text="", width=96, height=96, fg_color="black")
        self.slot1_canvas.grid(row=9, column=1, padx=5, pady=5)


        self.frame2 = customtkinter.CTkFrame(self)
        self.frame2.place(x=220, y=0)

        customtkinter.CTkLabel(self.frame2, text="슬롯2", width=190, height=30, fg_color="gray", corner_radius=6).grid(row=0, column=0, columnspan=2, padx=5, pady=5)
        customtkinter.CTkLabel(self.frame2, text="슬롯명", width=90, height=30).grid(row=1, column=0, padx=5, pady=5)
        self.slot2_name = customtkinter.CTkEntry(self.frame2, width=100, height=30)
        self.slot2_name.grid(row=1, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame2, text="입력키", width=90, height=30).grid(row=2, column=0, padx=5, pady=5)
        self.slot2_key = customtkinter.CTkEntry(self.frame2, width=100, height=30)
        self.slot2_key.grid(row=2, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame2, text="쿨타임", width=90, height=30).grid(row=3, column=0, padx=5, pady=5)
        self.slot2_cooltime = customtkinter.CTkEntry(self.frame2, width=100, height=30)
        self.slot2_cooltime.grid(row=3, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame2, text="Threshold", width=90, height=30).grid(row=4, column=0, padx=5, pady=5)
        self.slot2_threshold = customtkinter.CTkEntry(self.frame2, width=100, height=30)
        self.slot2_threshold.grid(row=4, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame2, text="캡처 x1", width=90, height=30).grid(row=5, column=0, padx=5, pady=5)
        self.slot2_x1 = customtkinter.CTkEntry(self.frame2, width=100, height=30)
        self.slot2_x1.grid(row=5, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame2, text="캡처 y1", width=90, height=30).grid(row=6, column=0, padx=5, pady=5)
        self.slot2_y1 = customtkinter.CTkEntry(self.frame2, width=100, height=30)
        self.slot2_y1.grid(row=6, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame2, text="캡처 x2", width=90, height=30).grid(row=7, column=0, padx=5, pady=5)
        self.slot2_x2 = customtkinter.CTkEntry(self.frame2, width=100, height=30)
        self.slot2_x2.grid(row=7, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame2, text="캡처 y2", width=90, height=30).grid(row=8, column=0, padx=5, pady=5)
        self.slot2_y2 = customtkinter.CTkEntry(self.frame2, width=100, height=30)
        self.slot2_y2.grid(row=8, column=1, padx=5, pady=5)

        self.slot2_target_btn = customtkinter.CTkButton(self.frame2, text="대상 이미지", width=90, height=30, command=lambda: self.load_img(self.slot2_canvas))
        self.slot2_target_btn.grid(row=9, column=0, padx=5, pady=5)
        self.slot2_canvas = customtkinter.CTkLabel(self.frame2, text="", width=96, height=96, fg_color="black")
        self.slot2_canvas.grid(row=9, column=1, padx=5, pady=5)

        self.frame3 = customtkinter.CTkFrame(self)
        self.frame3.place(x=430, y=0)

        customtkinter.CTkLabel(self.frame3, text="슬롯3", width=190, height=30, fg_color="gray", corner_radius=6).grid(row=0, column=0, columnspan=2, padx=5, pady=5)
        customtkinter.CTkLabel(self.frame3, text="슬롯명", width=90, height=30).grid(row=1, column=0, padx=5, pady=5)
        self.slot3_name = customtkinter.CTkEntry(self.frame3, width=100, height=30)
        self.slot3_name.grid(row=1, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame3, text="입력키", width=90, height=30).grid(row=2, column=0, padx=5, pady=5)
        self.slot3_key = customtkinter.CTkEntry(self.frame3, width=100, height=30)
        self.slot3_key.grid(row=2, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame3, text="쿨타임", width=90, height=30).grid(row=3, column=0, padx=5, pady=5)
        self.slot3_cooltime = customtkinter.CTkEntry(self.frame3, width=100, height=30)
        self.slot3_cooltime.grid(row=3, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame3, text="Threshold", width=90, height=30).grid(row=4, column=0, padx=5, pady=5)
        self.slot3_threshold = customtkinter.CTkEntry(self.frame3, width=100, height=30)
        self.slot3_threshold.grid(row=4, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame3, text="캡처 x1", width=90, height=30).grid(row=5, column=0, padx=5, pady=5)
        self.slot3_x1 = customtkinter.CTkEntry(self.frame3, width=100, height=30)
        self.slot3_x1.grid(row=5, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame3, text="캡처 y1", width=90, height=30).grid(row=6, column=0, padx=5, pady=5)
        self.slot3_y1 = customtkinter.CTkEntry(self.frame3, width=100, height=30)
        self.slot3_y1.grid(row=6, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame3, text="캡처 x2", width=90, height=30).grid(row=7, column=0, padx=5, pady=5)
        self.slot3_x2 = customtkinter.CTkEntry(self.frame3, width=100, height=30)
        self.slot3_x2.grid(row=7, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame3, text="캡처 y2", width=90, height=30).grid(row=8, column=0, padx=5, pady=5)
        self.slot3_y2 = customtkinter.CTkEntry(self.frame3, width=100, height=30)
        self.slot3_y2.grid(row=8, column=1, padx=5, pady=5)

        self.slot3_target_btn = customtkinter.CTkButton(self.frame3, text="대상 이미지", width=90, height=30, command=lambda: self.load_img(self.slot3_canvas))
        self.slot3_target_btn.grid(row=9, column=0, padx=5, pady=5)
        self.slot3_canvas = customtkinter.CTkLabel(self.frame3, text="", width=96, height=96, fg_color="black")
        self.slot3_canvas.grid(row=9, column=1, padx=5, pady=5)

        self.frame4 = customtkinter.CTkFrame(self)
        self.frame4.place(x=640, y=0)

        customtkinter.CTkLabel(self.frame4, text="슬롯4", width=190, height=30, fg_color="gray", corner_radius=6).grid(row=0, column=0, columnspan=2, padx=5, pady=5)
        customtkinter.CTkLabel(self.frame4, text="슬롯명", width=90, height=30).grid(row=1, column=0, padx=5, pady=5)
        self.slot4_name = customtkinter.CTkEntry(self.frame4, width=100, height=30)
        self.slot4_name.grid(row=1, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame4, text="입력키", width=90, height=30).grid(row=2, column=0, padx=5, pady=5)
        self.slot4_key = customtkinter.CTkEntry(self.frame4, width=100, height=30)
        self.slot4_key.grid(row=2, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame4, text="쿨타임", width=90, height=30).grid(row=3, column=0, padx=5, pady=5)
        self.slot4_cooltime = customtkinter.CTkEntry(self.frame4, width=100, height=30)
        self.slot4_cooltime.grid(row=3, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame4, text="Threshold", width=90, height=30).grid(row=4, column=0, padx=5, pady=5)
        self.slot4_threshold = customtkinter.CTkEntry(self.frame4, width=100, height=30)
        self.slot4_threshold.grid(row=4, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame4, text="캡처 x1", width=90, height=30).grid(row=5, column=0, padx=5, pady=5)
        self.slot4_x1 = customtkinter.CTkEntry(self.frame4, width=100, height=30)
        self.slot4_x1.grid(row=5, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame4, text="캡처 y1", width=90, height=30).grid(row=6, column=0, padx=5, pady=5)
        self.slot4_y1 = customtkinter.CTkEntry(self.frame4, width=100, height=30)
        self.slot4_y1.grid(row=6, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame4, text="캡처 x2", width=90, height=30).grid(row=7, column=0, padx=5, pady=5)
        self.slot4_x2 = customtkinter.CTkEntry(self.frame4, width=100, height=30)
        self.slot4_x2.grid(row=7, column=1, padx=5, pady=5)

        customtkinter.CTkLabel(self.frame4, text="캡처 y2", width=90, height=30).grid(row=8, column=0, padx=5, pady=5)
        self.slot4_y2 = customtkinter.CTkEntry(self.frame4, width=100, height=30)
        self.slot4_y2.grid(row=8, column=1, padx=5, pady=5)

        self.slot4_target_btn = customtkinter.CTkButton(self.frame4, text="대상 이미지", width=90, height=30, command=lambda: self.load_img(self.slot4_canvas))
        self.slot4_target_btn.grid(row=9, column=0, padx=5, pady=5)
        self.slot4_canvas = customtkinter.CTkLabel(self.frame4, text="", width=96, height=96, fg_color="black")
        self.slot4_canvas.grid(row=9, column=1, padx=5, pady=5)

        customtkinter.CTkButton(self, text="저장", width=100, height=30, command=self.save).place(x=10, y=480)



    def load_target_img(self):
        filename = customtkinter.filedialog.askopenfilename()
        return filename

    def load_img(self, target_widget):
        print(target_widget)
        filename = self.load_target_img()
        img_np = np.fromfile(filename, np.uint8)
        img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_tk = customtkinter.CTkImage(light_image=PIL.Image.fromarray(img_rgb), size=(96, 96))
        target_widget.configure(image=img_tk)


    def apply_data(self):
        print("apply")

    def save(self):
        print("save")




class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title("만들오토")
        self.attributes('-topmost',True)
        self.geometry("330x420+50+200")
        # customtkinter.set_widget_scaling(1.5)
        # customtkinter.set_window_scaling(1.5)

        self.paused = False

        self.camera = dxcam.create(output_color="BGR")
        self.camera.start()
        frame = self.camera.get_latest_frame()
        self.screen_width = frame.shape[1]
        self.screen_height = frame.shape[0]

        self.canvas = customtkinter.CTkLabel(self, text="", width=320, height=180, fg_color="gray")
        self.canvas.place(x=5, y=0)

        # Mouse info
        self.mouse_info = customtkinter.CTkLabel(self, text="POS :")
        self.mouse_info.place(x=15, y=180)
        
        # Timer Frame
        self.timer_frame = customtkinter.CTkFrame(self, width=100, height=160)
        self.timer_frame.place(x=5, y=210)
        customtkinter.CTkButton(self.timer_frame, text="타이머", width=90, height=30, fg_color="gray40", command=self.timer_setting).place(x=5, y=5)
        self.timer1 = customtkinter.CTkCheckBox(self.timer_frame, text="슬롯1")
        self.timer1.place(x=5, y=40)
        self.timer2 = customtkinter.CTkCheckBox(self.timer_frame, text="슬롯2")
        self.timer2.place(x=5, y=70)
        self.timer3 = customtkinter.CTkCheckBox(self.timer_frame, text="슬롯3")
        self.timer3.place(x=5, y=100)
        self.timer4 = customtkinter.CTkCheckBox(self.timer_frame, text="슬롯4")
        self.timer4.place(x=5, y=130)

        # HP Fram4
        self.hp_frame = customtkinter.CTkFrame(self, width=100, height=160)
        self.hp_frame.place(x=110, y=210)
        customtkinter.CTkButton(self.hp_frame, text="HP슬롯", width=90, height=30, fg_color="gray40", command=self.hp_setting).place(x=5, y=5)
        self.hp1 = customtkinter.CTkCheckBox(self.hp_frame, text="슬롯1")
        self.hp1.place(x=5, y=40)
        self.hp2 = customtkinter.CTkCheckBox(self.hp_frame, text="슬롯2")
        self.hp2.place(x=5, y=70)
        self.hp3 = customtkinter.CTkCheckBox(self.hp_frame, text="슬롯3")
        self.hp3.place(x=5, y=100)
        self.hp4 = customtkinter.CTkCheckBox(self.hp_frame, text="슬롯4")
        self.hp4.place(x=5, y=130)

        # IMG Frame
        self.img_frame = customtkinter.CTkFrame(self, width=100, height=160)
        self.img_frame.place(x=215, y=210)
        customtkinter.CTkButton(self.img_frame, text="IMG슬롯", width=90, height=30, fg_color="gray40", command=self.img_setting).place(x=5, y=5)
        self.img1 = customtkinter.CTkCheckBox(self.img_frame, text="슬롯1")
        self.img1.place(x=5, y=40)
        self.img2 = customtkinter.CTkCheckBox(self.img_frame, text="슬롯2")
        self.img2.place(x=5, y=70)
        self.img3 = customtkinter.CTkCheckBox(self.img_frame, text="슬롯3")
        self.img3.place(x=5, y=100)
        self.img4 = customtkinter.CTkCheckBox(self.img_frame, text="슬롯4")
        self.img4.place(x=5, y=130)

        # Button Frame
        self.btn_pause = customtkinter.CTkButton(self, width=150, height=30, text="일시 정지", command=self.pause)
        self.btn_pause.place(x=10, y=380)

        self.timer_setting_window = None
        self.hp_setting_window = None
        self.img_setting_window = None
        customtkinter.CTkButton(self, width=150, height=30, text="설정 열기", command=self.test).place(x=170, y=380)

        # Pause label
        self.pause_label = customtkinter.CTkLabel(self, text="일시 정지", fg_color="gray", corner_radius=0, width=330, height=370)

        self.update()

    def test(self):
        print(data)

    def pause(self):
        self.paused = not self.paused
        if self.paused:
            self.pause_label.place(x=0, y=0)
            self.btn_pause.configure(text="정지 해제")
        else:
            self.pause_label.place_forget()
            self.btn_pause.configure(text="일시 정지")
        

    def timer_setting(self):
        if self.timer_setting_window is None or not self.timer_setting_window.winfo_exists():
            self.timer_setting_window = TimerSetting(self)
        else:
            self.timer_setting_window.focus()
        self.timer_setting_window.apply_data()


    def hp_setting(self):
        if self.hp_setting_window is None or not self.hp_setting_window.winfo_exists():
            self.hp_setting_window = HpslotSetting(self)
        else:
            self.hp_setting_window.focus()
        self.hp_setting_window.apply_data()

    def img_setting(self):
        if self.img_setting_window is None or not self.img_setting_window.winfo_exists():
            self.img_setting_window = IMGslotSetting(self)
        else:
            self.img_setting_window.focus()
        self.img_setting_window.apply_data()

    def apply(self):
        self.timer1.configure(text=data["timerslot"]["slot1"]["name"])
        self.timer2.configure(text=data["timerslot"]["slot2"]["name"])
        self.timer3.configure(text=data["timerslot"]["slot3"]["name"])
        self.timer4.configure(text=data["timerslot"]["slot4"]["name"])

        self.hp1.configure(text=data["hpslot"]["slot1"]["name"])
        self.hp2.configure(text=data["hpslot"]["slot2"]["name"])
        self.hp3.configure(text=data["hpslot"]["slot3"]["name"])
        self.hp4.configure(text=data["hpslot"]["slot4"]["name"])

        self.img1.configure(text=data["imgslot"]["slot1"]["name"])
        self.img2.configure(text=data["imgslot"]["slot2"]["name"])
        self.img3.configure(text=data["imgslot"]["slot3"]["name"])
        self.img4.configure(text=data["imgslot"]["slot4"]["name"])
        


    def update(self):
        frame = self.camera.get_latest_frame()
        thumbnail = cv2.resize(frame, dsize=(320,180), interpolation=cv2.INTER_AREA)
        img_rgb = cv2.cvtColor(thumbnail, cv2.COLOR_BGR2RGB)
        img_tk = customtkinter.CTkImage(light_image=PIL.Image.fromarray(img_rgb), size=(320,180))
        self.canvas.configure(image=img_tk)

        flags, hcursor, (x,y) = win32gui.GetCursorInfo()
        sx = int(x/self.screen_width*1000)
        sy = int(y/self.screen_height*1000)
        self.mouse_info.configure(text=f"POS : Capture({x},{y}) Input({sx},{sy})")

        self.after(200, self.update)



app = App()
app.mainloop()