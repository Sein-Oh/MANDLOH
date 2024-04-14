from blessed import Terminal
import time, os, platform
 
term = Terminal()

def clear():
    command = "cls" if "Windows" in platform.platform() else "clear"
    os.system(command)
 
def draw(x, y, text, color=term.normal):
    print(f"{term.move_xy(x, y)}{color}{text}{term.normal}")

def draw_frame(x, y, w, h, title="", color=term.normal):
    for j in range(h):
        draw(x, y+j, "│" + (" " * (w-1)) + "│", color)
    draw(x, y, "╭" + ("─" * (w-1)) + "╮", color)
    draw(x, y+h-1, "╰" + ("─" * (w-1)) + "╯", color)
    if title: draw(x+2, y, title, color)

def draw_time(x, y, color=term.normal):
    now = time.localtime()
    print(f"{term.move_xy(x, y)}{color}[{now.tm_mon}-{now.tm_mday} {now.tm_hour}:{now.tm_min}:{str(now.tm_sec).rjust(2, '0')}]{term.normal}")

clear()
main_color = term.normal
key = ""
while True:
    with term.cbreak(), term.hidden_cursor():
        val = term.inkey(timeout=0.2)
        key = val.name if val.is_sequence else val

        draw_time(0, 0, term.on_blue)
        draw_frame(0, 1, 20, 5, '메인메뉴', main_color)
        # draw_frame(22, 1, 20, 5, "서브메뉴", term.green)
        draw(2, 2, key)
        

        print(term.move_xy(0, term.height-3))
