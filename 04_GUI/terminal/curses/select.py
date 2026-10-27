import curses

def select(menu, width=20):
    stdscr = curses.initscr()
    stdscr.keypad(True)
    curses.cbreak()
    curses.noecho()
    curses.curs_set(False)
    curses.mousemask(True)

    h, w = stdscr.getmaxyx()
    start_x, start_y = w//2 - width//2, 5
    idx = 0

    while True:
        stdscr.addstr(start_y, start_x, "[SELECT MENU]".center(width), curses.A_BLINK)
        for i, item in enumerate(menu):
            stdscr.addstr(start_y+i+1, start_x, item.center(width), curses.A_REVERSE if idx == i else curses.A_NORMAL)
        key = stdscr.getch()
        
        # handle key input
        if key == ord("q"):
            curses.endwin()
            return None
        elif key == curses.KEY_UP and idx > 0:
            idx -= 1
        elif key == curses.KEY_DOWN and idx < len(menu) -1:
            idx += 1
        elif key == curses.KEY_ENTER or key == 10 or key == 13:
            curses.endwin()
            return menu[idx]
        
        # handle mouse input
        if key == curses.KEY_MOUSE:
            mx, my = curses.getmouse()[1:3]
            if mx in range(start_x, start_x+w) and my in range(start_y+1, start_y+len(menu)+1):
                idx = my - start_y - 1
                curses.endwin()
                return menu[idx]


def multi_select(menu, width=20, checked=None):
    if checked == None:
        checked = [False for m in menu]
    stdscr = curses.initscr()
    stdscr.keypad(True)
    curses.cbreak()
    curses.noecho()
    curses.curs_set(False)
    curses.mousemask(True)

    h, w = stdscr.getmaxyx()
    start_x, start_y = w//2 - width//2, 5
    idx = 0
    acc = 0

    while True:
        stdscr.addstr(start_y, start_x, "[SELECT MENU]".center(width), curses.A_BLINK)
        for i, item in enumerate(menu):
            chk = "[V]" if checked[i] == True else "[ ]"
            stdscr.addstr(start_y+i+1, start_x, f"{chk} {item}".ljust(width), curses.A_REVERSE if idx == i else curses.A_NORMAL)
        stdscr.addstr(start_y+len(menu)+2, start_x+1, "[ACCEPT]", curses.A_REVERSE if acc == 1 else curses.A_NORMAL)
        stdscr.addstr(start_y+len(menu)+2, start_x+10, "[CANCEL]", curses.A_REVERSE if acc == 2 else curses.A_NORMAL)
        
        key = stdscr.getch()
        
        # handle key input
        if key == ord("q"):
            curses.endwin()
            return None
        elif key == curses.KEY_UP and idx > 0:
            acc = 0
            idx -= 1
        elif key == curses.KEY_DOWN and idx < len(menu) -1:
            acc = 0
            idx += 1
        elif key == curses.KEY_ENTER or key == 10 or key == 13 or key == ord(" "):
            if acc == 0:
                checked[idx] = not checked[idx]
            else:
                curses.endwin()
                return checked if acc == 1 else None
        elif key == curses.KEY_LEFT:
            acc = 1
        elif key == curses.KEY_RIGHT:
            acc = 2
        
        # handle mouse input
        if key == curses.KEY_MOUSE:
            mx, my = curses.getmouse()[1:3]
            if mx in range(start_x, start_x+w) and my in range(start_y+1, start_y+len(menu)+1):
                idx = my - start_y - 1
                checked[idx] = not checked[idx]