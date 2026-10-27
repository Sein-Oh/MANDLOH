from blessed import Terminal
import time
term = Terminal()

slots = {
    'slot1': False,
    'slot2': False,
    'slot3': False,
    'slot4': False
}
print(term.clear)

with term.cbreak(), term.hidden_cursor(), term.fullscreen(), term.mouse_enabled(report_motion=False):
    while True:
        inp = term.inkey(timeout=0.2)
        my = inp.mouse_xy[1]
        if my > -1 and inp.name == 'MOUSE_LEFT':
            if my == 1:
                slots['slot1'] = not slots['slot1']
            elif my == 2:
                slots['slot2'] = not slots['slot2']
            elif my == 3:
                slots['slot3'] = not slots['slot3']
            elif my == 4:
                slots['slot4'] = not slots['slot4']

        with term.location(0, 1):
            for key in slots:
                print(f'{key} : {slots[key]}'.ljust(30))

        time.sleep(0.01)
