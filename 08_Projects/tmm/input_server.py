import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import queue
from flask import Flask, request
from datetime import datetime
from werkzeug.serving import make_server
import requests
import keyboard
import mouse
import time
from urllib.parse import unquote

# -------------------------------
# Flask 서버 정의
# -------------------------------
app = Flask(__name__)
log_queue = queue.Queue()

@app.route('/<path:cmd>')
def index(cmd):
    # 브라우저 요청 제외
    if cmd in ["service-worker.js", "favicon.ico"]:
        return "", 204

    # URL 디코딩 + ? 제거
    full_path = unquote(request.full_path)  # %20 -> 공백
    full_path = full_path.split('?', 1)[0]  # 쿼리 제거
    log_queue.put(f"[{datetime.now().strftime('%H:%M:%S')}] http://{request.host}{full_path}")

    # / 제거 후 띄어쓰기 기준 분리
    commands = full_path.strip("/").split()
    for c in commands:
        if c.startswith('-'):  # 지연 처리
            try:
                time.sleep(float(c[1:]))
            except Exception as e:
                log_queue.put(f"[ERROR] 지연 처리 실패: {c} ({e})")
        elif ',' in c:  # 마우스 좌표
            try:
                x_str, y_str = c.split(',', 1)
                x = int(x_str)
                y = int(y_str)
                mouse.move(x, y, duration=0.1)
                mouse.click()
            except Exception as e:
                log_queue.put(f"[ERROR] 좌표 처리 실패: {c} ({e})")
        else:  # 일반 문자
            try:
                # keyboard.write(c)
                keyboard.press_and_release(c)
            except Exception as e:
                log_queue.put(f"[ERROR] 키보드 입력 실패: {c} ({e})")

    return "", 204

# -------------------------------
# Flask 서버 스레드
# -------------------------------
class FlaskServerThread(threading.Thread):
    def __init__(self, host, port):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.server = make_server(host, port, app)
        self.ctx = app.app_context()
        self.ctx.push()
        self.is_running = True

    def run(self):
        while self.is_running:
            self.server.handle_request()

    def stop(self):
        self.is_running = False
        try:
            requests.get(f"http://{self.host}:{self.port}/shutdown_check", timeout=0.5)
        except Exception:
            pass

@app.route('/shutdown_check')
def shutdown_check():
    return "OK"

# -------------------------------
# Tkinter UI
# -------------------------------
server_thread = None

def update_url_label(*args):
    """Host/Port 입력 시 실시간 URL 갱신"""
    host = host_var.get().strip()
    port = port_var.get().strip()
    if host and port.isdigit():
        url_label.config(text=f"http://{host}:{port}/")
    else:
        url_label.config(text="http://—.—.—.—:—/")

def start_server():
    """Flask 서버 시작"""
    global server_thread

    host = host_var.get().strip()
    port_str = port_var.get().strip()

    if not host:
        messagebox.showwarning("입력 오류", "Host를 입력하세요.")
        return
    if not port_str.isdigit():
        messagebox.showwarning("입력 오류", "Port는 숫자만 입력하세요.")
        return

    port = int(port_str)
    try:
        server_thread = FlaskServerThread(host, port)
        server_thread.start()
    except OSError as e:
        messagebox.showerror("서버 오류", f"포트 {port}를 사용할 수 없습니다.\n{e}")
        return

    url = f"http://{host}:{port}"
    msg = f"[{datetime.now().strftime('%H:%M:%S')}] 서버 시작. URL: {url}/"
    log_queue.put(msg)

    # 버튼 상태 및 UI 변경
    start_button.config(text="서버 실행 중", state=tk.DISABLED)
    host_entry.config(state=tk.DISABLED)
    port_entry.config(state=tk.DISABLED)

def update_log():
    """Flask 로그 표시"""
    while not log_queue.empty():
        log_box.insert(tk.END, log_queue.get() + "\n")
        log_box.see(tk.END)
    root.after(500, update_log)

def on_close():
    """창 닫을 때 자연스럽게 종료"""
    global server_thread
    if server_thread and server_thread.is_alive():
        server_thread.stop()
        # join을 걸지 않고 즉시 종료 (GUI 블로킹 방지)
        log_queue.put("서버 종료 중... 창을 닫습니다.")
    root.after(300, root.destroy)  # 약간의 딜레이 후 종료 (shutdown 스레드 실행 보장)

# -------------------------------
# UI 구성
# -------------------------------
root = tk.Tk()
root.title("Keyboard/Mouse Input Server")
root.protocol("WM_DELETE_WINDOW", on_close)
root.wm_attributes("-topmost", True) 

root.geometry("540x140")

# 화면 크기 얻기
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

# 창 크기
window_width = 540
window_height = 140

# 우측 하단 위치 계산 (조금 여백 줌)
x_pos = screen_width - window_width - 20
y_pos = screen_height - window_height - 80

# 위치 반영
root.geometry(f"{window_width}x{window_height}+{x_pos}+{y_pos}")


frame = tk.Frame(root)
frame.pack(pady=5)

host_var = tk.StringVar(value="localhost")
port_var = tk.StringVar(value="8000")
host_var.trace_add("write", update_url_label)
port_var.trace_add("write", update_url_label)

tk.Label(frame, text="Host:").grid(row=0, column=0, padx=3)
host_entry = tk.Entry(frame, textvariable=host_var, width=15)
host_entry.grid(row=0, column=1, padx=3)

tk.Label(frame, text="Port:").grid(row=0, column=2, padx=3)
port_entry = tk.Entry(frame, textvariable=port_var, width=7)
port_entry.grid(row=0, column=3, padx=3)

url_label = tk.Label(frame, text="http://localhost:8000/", fg="blue", font=("Arial", 10, "italic"))
url_label.grid(row=0, column=4, padx=5)

start_button = tk.Button(frame, text="서버 시작", width=12, command=start_server)
start_button.grid(row=0, column=5, padx=6)

log_box = scrolledtext.ScrolledText(root, width=63, height=5)
log_box.pack(padx=10, pady=5)

update_url_label()
update_log()

root.mainloop()
