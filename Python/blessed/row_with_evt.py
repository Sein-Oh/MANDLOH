from blessed import Terminal
import time

term = Terminal()


def prompt(legend, msg):
        print(term.clear)
        text = ''
        while True:
            title(0, f' {legend} ')
            draw(1, f'{msg} {text}'.ljust(term.width))
            inp = term.inkey()
            pressed_key = inp.name if inp.is_sequence else inp
            if 'KEY' in pressed_key:
                if pressed_key == 'KEY_BACKSPACE':
                    text = text[:-1]
                elif pressed_key == 'KEY_ENTER':
                    print(term.clear)
                    return text
                elif pressed_key == 'KEY_EACAPE':
                    return ''
            else:                
                text = text + pressed_key
            

def event_handler(event):
    if event == 'COMMAND':
        print(event)


def draw(row, text, mouse_y=-1, event=None):
    with term.location(0, row):
        print(text)
    if mouse_y == row:
        event_handler(event)


def title(row, label, mouse_y=-1, event=None):
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
            mouse_y = inp.mouse_xy[1] if inp.mouse_xy else -1
            # Keyboard
            pressed_key = inp.name if inp.is_sequence else inp
            
            
            title(0, ' HEADER ', mouse_y, 'COMMAND')
            draw(2, term.black_on_white('Hello world!!'), mouse_y)
            draw(3, term.black_on_white('Hello world!!'), mouse_y, 'COMMAND')
            
            if pressed_key == 'KEY_F1':
                rtn = prompt('PROMPT', 'Your message :')
                print(rtn)
                
            time.sleep(0.01)

except KeyboardInterrupt:
    pass

finally:
    print(term.normal_cursor(), end='')
    print(term.exit_fullscreen(), end='')
