from tkinter import filedialog, simpledialog
import customtkinter

class Slot(customtkinter.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.run_var = customtkinter.BooleanVar(value=False)
        self.run = customtkinter.CTkSwitch(self, text="실행", variable=self.run_var, onvalue=True, offvalue=False)
        self.run.grid(row=0, column=0, padx=5, pady=3)

        self.btn_file = customtkinter.CTkButton(self, text="파일선택", command=self.ask_file, width=100)
        self.btn_file.grid(row=1, column=0, padx=5, pady=3)
        self.lbl_file_name = customtkinter.CTkLabel(self, text="비어있음", width=200)
        self.lbl_file_name.grid(row=1, column=1)

        self.btn_key = customtkinter.CTkButton(self, text="입력키", command=self.ask_text, width=100)
        self.btn_key.grid(row=2, column=0, padx=5, pady=3)
        self.lbl_key = customtkinter.CTkLabel(self, text="비어있음", width=200)
        self.lbl_key.grid(row=2, column=1, padx=5, pady=3)

        self.btn_cool = customtkinter.CTkButton(self, text="쿨타임", width=100, command=lambda : self.ask_float(self.lbl_cool))
        self.btn_cool.grid(row=3, column=0, padx=5, pady=3)
        self.lbl_cool = customtkinter.CTkLabel(self, text="비어있음", width=200)
        self.lbl_cool.grid(row=3, column=1, padx=5, pady=3)

        self.btn_thres = customtkinter.CTkButton(self, text="유사도", width=100, command=lambda : self.ask_float(self.lbl_thres))
        self.btn_thres.grid(row=4, column=0, padx=5, pady=3)
        self.lbl_thres = customtkinter.CTkLabel(self, text="비어있음", width=200)
        self.lbl_thres.grid(row=4, column=1, padx=5, pady=3)


    def ask_file(self):
        file_path = filedialog.askopenfile()
        if file_path:
            full_path = file_path.name
            file_name = full_path.split("/")[-1]
            self.lbl_file_name.configure(text=file_name)

    def ask_text(self):
        answer = simpledialog.askstring(title="값을 입력하세요.", prompt="값을 입력하세요.")
        self.lbl_key.configure(text=answer)

    def ask_float(self, widget):
        answer = simpledialog.askfloat(title="값을 입력하세요.", prompt="값을 입력하세요.")
        widget.configure(text=answer)


class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("GUI")
        # self.geometry("460x180")
        # self.grid_columnconfigure(0, weight=1)
        # self.grid_rowconfigure(0, weight=1)

        self.my_frame = Slot(master=self)
        self.my_frame.grid(row=0, column=0, padx=5, pady=3, sticky="nsew")

        self.my_frame2 = Slot(master=self)
        self.my_frame2.grid(row=1, column=0, padx=5, pady=3, sticky="nsew")

        # self.select_frame = customtkinter.CTkFrame(self, width=500)
        # self.select_frame.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="nsw")
        
        # self.slot_1 = customtkinter.CTkCheckBox(self.select_frame, text="Slot-1")
        # self.slot_1.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="w")

        # self.slot_2 = customtkinter.CTkCheckBox(self.select_frame, text="Slot-2")
        # self.slot_2.grid(row=1, column=0, padx=10, pady=(10, 0), sticky="w")

app = App()
app.mainloop()