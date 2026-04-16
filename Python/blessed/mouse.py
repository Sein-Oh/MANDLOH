#!/usr/bin/env python
from blessed import Terminal
import time
term = Terminal()

if not term.does_mouse(report_motion=True):
    print("This terminal does not support mouse motion tracking!")
else:
    # Track current color for painting
    color_idx = 7
    num_colors = min(256, term.number_of_colors)
    header = "Mouse wheel sets color=[{0}], LEFT button paints, RIGHT erases, ^C:quit"

    def make_header():
        return term.home + term.center(header.format(term.color(color_idx)('█')))
    text = make_header()

    with term.cbreak(), term.fullscreen(), term.mouse_enabled(report_motion=False):
        while True:
            print(text, end='', flush=True)
            inp = term.inkey()
            if inp.name and inp.name.startswith("MOUSE_"):
                with term.location(0,5):
                    print(f"{inp.mouse_xy}".ljust(30))
            time.sleep(0.01)
