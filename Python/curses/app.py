import curses
import time
from StringProgressBar import progressBar


stdscr = curses.initscr()
curses.noecho()
curses.cbreak()
stdscr.keypad(True)
height, width = stdscr.getmaxyx()

curses.start_color()
curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
curses.init_pair(2, curses.COLOR_BLUE, curses.COLOR_BLACK)
curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)

win1 = curses.newwin(4, 40, 1, 0) # curses.newwin(height, width, begin_y, begin_x)

k = 0
idx = 0
while (k != ord("q")):
    win1.clear()
    win1.border(0)
    win1.addstr(0, 2, " MONITOR ", curses.color_pair(3))
    
    hp_bar = progressBar.filledBar(100, idx, 25, "-", "█")[0]
    win1.addstr(1, 2, "HP :")
    win1.addstr(1, 6, f"{str(idx).rjust(3)}%")
    win1.addstr(1, 11, f"[{hp_bar}]", curses.color_pair(1))
    
    mp_bar = progressBar.filledBar(100, idx, 25, "-", "█")[0]
    win1.addstr(2, 2, "HP :")
    win1.addstr(2, 6, f"{str(idx).rjust(3)}%")
    win1.addstr(2, 11, f"[{mp_bar}]", curses.color_pair(2))
    win1.refresh()
    
    time.sleep(0.2)
    stdscr.nodelay(1)
    k = stdscr.getch()
    idx += 1
curses.endwin()
