import curses
from StringProgressBar import progressBar

menu = ["USE", "KEY", "COUNT", "EXIT"]

def print_center(stdscr, text):
	stdscr.clear()
	h, w = stdscr.getmaxyx()
	x = w//2 - len(text)//2
	y = h//2
	stdscr.addstr(y, x, text)
	stdscr.refresh()

def main(stdscr):
    stdscr.timeout(200)
    stdscr.nodelay(1)
    curses.curs_set(0)
    curses.mousemask(1)

    curses.start_color()
    curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_BLUE, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)


    win1 = curses.newwin(4, 40, 1, 0) # curses.newwin(height, width, begin_y, begin_x)

    key = 0
    idx = 100
    sel = 0
    while (key != ord("q")):
        win1.clear()
        # win1.attron(curses.color_pair(2))
        win1.border(0)
        # win1.attroff(curses.color_pair(2))
        win1.addstr(0, 2, " MONITOR ", curses.color_pair(3))
        
        hp_bar = progressBar.filledBar(100, idx, 25, "-", "█")[0]
        win1.addstr(1, 2, "XX :")
        win1.addstr(1, 6, f"{str(idx).rjust(3)}%")
        win1.addstr(1, 11, f"[{hp_bar}]", curses.color_pair(1))
        
        mp_bar = progressBar.filledBar(100, idx, 25, "-", "█")[0]
        win1.addstr(2, 2, "YY :")
        win1.addstr(2, 6, f"{str(idx).rjust(3)}%")
        win1.addstr(2, 11, f"[{mp_bar}]", curses.color_pair(2))
        win1.refresh()

        for i, name in enumerate(menu):
            if i == sel:
                stdscr.attron(curses.color_pair(3))
                stdscr.addstr(i + 5, 2, name)
                stdscr.attroff(curses.color_pair(3))
            else:
                stdscr.addstr(i + 5, 2, name)

        
        key = stdscr.getch()
        if key == curses.KEY_UP and sel > 0:
            sel -= 1
        elif key == curses.KEY_DOWN and sel < len(menu)-1:
            sel += 1
        elif key == ord('i'):
            stdscr.nodelay(0)
            curses.echo()
            stdscr.timeout(-1)
            stdscr.clear()
            stdscr.refresh()
            s = stdscr.getstr(10, 5, 15)
            stdscr.timeout(200)



        if key == curses.KEY_MOUSE:
            mx, my= curses.getmouse()[1:3]
            stdscr.addstr(10, 2, f"{str(mx).rjust(3)}, {str(my).rjust(3)}")
            if mx in range(2, 8) and my in range(5, 9):
                sel = my -5
        

        idx -= 1
        stdscr.refresh()


curses.wrapper(main)
