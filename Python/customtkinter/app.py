import cv2
import dxcam
import numpy as np
import PIL.Image, PIL.ImageTk
import customtkinter
from tkinter import filedialog

delay = 500

def apply_image(img_cv, widget):
    widget.configure(text="")
    widget_width, widget_height = widget.cget("width"), widget.cget("height")
    img_height, img_width, img_channel = img_cv.shape
    width_ratio = widget_width / img_width
    height_ratio = widget_height / img_height
    ratio = min(width_ratio, height_ratio)
    if ratio < 1:
        img_cv = cv2.resize(img_cv, dsize=(0,0), fx=ratio, fy=ratio, interpolation=cv2.INTER_LINEAR)
    img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
    img_tk = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(img_rgb))
    widget.configure(image=img_tk)

def find_img(background, target, threshold):
    background = cv2.cvtColor(background, cv2.COLOR_BGR2GRAY)
    target = cv2.cvtColor(target, cv2.COLOR_BGR2GRAY)
    res = cv2.matchTemplate(background, target, cv2.TM_CCOEFF_NORMED)
    res = np.where(res>=threshold) # res에서 threshold보다 큰 값만 취한다.
    point = []
    for pt in zip(*res[::-1]):
        point.append(pt)
    print(point)
    return len(point) # 찾음여부만 확인하기 위해 길이로 리턴한다.


class Slot(customtkinter.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.run_var = customtkinter.BooleanVar(value=False)
        self.run = customtkinter.CTkSwitch(self, text="실행", variable=self.run_var, onvalue=True, offvalue=False)
        self.run.grid(row=0, column=0, columnspan=2 ,padx=3, pady=3)

        self.cnv_preview = customtkinter.CTkLabel(self, text="파일선택", width=160, height=90, fg_color="lightgray")
        self.cnv_preview.bind("<ButtonPress-1>", command=lambda _: self.ask_file())
        self.cnv_preview.grid(row=1, column=0, columnspan=2, padx=3, pady=3)

        self.btn_key = customtkinter.CTkButton(self, text="입력키", width=60, command=lambda: self.ask_text(self.lbl_key))
        self.btn_key.grid(row=2, column=0, padx=3, pady=3)
        self.lbl_key = customtkinter.CTkLabel(self, text="비어있음", width=100, fg_color="lightgray")
        self.lbl_key.grid(row=2, column=1, padx=3, pady=3)

        self.btn_cool = customtkinter.CTkButton(self, text="쿨타임", width=60, command=lambda : self.ask_text(self.lbl_cool))
        self.btn_cool.grid(row=3, column=0, padx=3, pady=3)
        self.lbl_cool = customtkinter.CTkLabel(self, text="비어있음", width=100, fg_color="lightgray")
        self.lbl_cool.grid(row=3, column=1, padx=3, pady=3)


        self.cnv_roi = customtkinter.CTkLabel(self, text="ROI화면", width=160, height=90, fg_color="lightgray")
        self.cnv_roi.grid(row=1, column=2, columnspan=2, padx=3, pady=3)

        self.btn_roi = customtkinter.CTkButton(self, text="ROI", width=60, command=lambda: self.ask_text(self.lbl_roi))
        self.btn_roi.grid(row=2, column=2, padx=3, pady=3)
        self.lbl_roi = customtkinter.CTkLabel(self, text="전체화면", width=100, fg_color="lightgray")
        self.lbl_roi.grid(row=2, column=3, padx=3, pady=3)

        self.btn_thres = customtkinter.CTkButton(self, text="유사도", width=60, command=lambda : self.ask_text(self.lbl_thres))
        self.btn_thres.grid(row=3, column=2, padx=3, pady=3)
        self.lbl_thres = customtkinter.CTkLabel(self, text="0.8", width=100, fg_color="lightgray")
        self.lbl_thres.grid(row=3, column=3, padx=3, pady=3)

    def ask_file(self):
        file_path = filedialog.askopenfile()
        if file_path:
            full_path = file_path.name
            self.img_target = cv2.imread(full_path)
            apply_image(self.img_target, self.cnv_preview)

    def ask_text(self, widget):
        answer = customtkinter.CTkInputDialog(text="값을 입력하세요.", title="")
        value = answer.get_input()
        if value:
            widget.configure(text=value)


class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.camera = dxcam.create(output_color="BGR")
        self.camera.start(target_fps=2)

        self.title("GUI")

        self.cnv_preview = customtkinter.CTkLabel(self, text="", width=320, height=180, fg_color="gray")
        self.cnv_preview.grid(row=0, column=0, padx=3, pady=3)

        self.slot1 = Slot(master=self)
        self.slot1.grid(row=2, column=0, padx=3, pady=3, sticky="nsew")

        self.slot2 = Slot(master=self)
        self.slot2.grid(row=3, column=0, padx=3, pady=3, sticky="nsew")

        self.image_update()

    def image_update(self):
        self.frame = self.camera.get_latest_frame()
        frame_resize = cv2.resize(self.frame, dsize=(320,180), interpolation=cv2.INTER_LINEAR)
        apply_image(frame_resize, self.cnv_preview)

        self.after(delay, self.image_update)

        # ROI화면 업데이트
        slots = [self.slot1, self.slot2]
        for slot in slots:
            if slot.lbl_roi.cget("text") == "전체화면":
                apply_image(frame_resize, slot.cnv_roi)
            else:
                x,y,w,h = map(int, slot.lbl_roi.cget("text").split(","))
                apply_image(self.frame[y:y+h,x:x+w], slot.cnv_roi)

app = App()
app.mainloop()
