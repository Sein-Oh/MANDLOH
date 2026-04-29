from blessed import Terminal
import time

term = Terminal()


def event_handler(event):
    # with term.location(0, 10):
    print(event.ljust(term.width))


def draw(row, text, mouse_y, event=""):
    with term.location(0, row):
        print(text)
    if mouse_y == row:
        event_handler(event)


def title(row, label, mouse_y, event=""):
    inner_width = term.width - 1
    with term.location(0, row):
        print(term.white('─' * 2) + term.black_on_white(label) + term.white('─' * (inner_width - len(label) - 2)))
    if mouse_y == row:
        event_handler(event)


try:
    with term.cbreak(), term.hidden_cursor(), term.fullscreen(), term.mouse_enabled():
        while True:
            inp = term.inkey(timeout=0)
            # Mouse
            mouse_y = inp.mouse_xy[1] if inp.name == 'MOUSE_LEFT' else -1
            # Keyboard
            pressed_key = inp.name if inp.is_sequence else inp
            
            title(0, 'HEADER', mouse_y, 'HEADER')
            draw(2, term.black_on_white('Hello world!!'), mouse_y, f'{mouse_y}')
            draw(3, term.black_on_white('Hello world!!'), mouse_y, f'{mouse_y}')
            time.sleep(0.01)

except KeyboardInterrupt:
    pass

finally:
    print(term.normal_cursor(), end='')
    print(term.exit_fullscreen(), end='')
