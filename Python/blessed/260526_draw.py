from blessed import Terminal
from wcwidth import wcwidth
import time

term = Terminal()

def event_handler(command):
    if command:
        print(command)


def draw(x, y, width, text, color=None, command=None, align='left'):
    text_display_width = sum(wcwidth(c) for c in text)
    if text_display_width > width:
        truncated_text = ''
        current_sum = 0
        for char in text:
            char_w = wcwidth(char)
            if current_sum + char_w <= width:
                truncated_text += char
                current_sum += char_w
            else:
                break
            
        output_text = truncated_text
        filan_text_width = sum(wcwidth(c) for c in output_text)
    else:
        output_text = text
        filan_text_width = text_display_width
        
    padding_size = width - filan_text_width
    if align == 'right':
        final_output(' ' * padding_size) + output_text
    elif align == 'center':
        left_pad = padding_size // 2
        right_pad = padding_size - left_pad
        final_output = (' ' * left_pad) + output_text + (' ' * right_pad)
    else:
        final_output = output_text + (' ' * padding_size)
    
    with term.location(x, y):
        if color:
            print(color(final_output))
        else:
            print(final_output)
    
    if mouse_y == y and x <= mouse_x < x + width:
        event_handler(command)
        
try:
    with term.cbreak(), term.hidden_cursor(), term.fullscreen(), term.mouse_enabled():
        while True:
            inp = term.inkey(timeout=0)
            mouse_x = inp.mouse_xy[0] if inp.mouse_xy else -1
            mouse_y = inp.mouse_xy[1] if inp.mouse_xy else -1
            pressed_key = inp.name if inp.is_sequence else inp
            
            if pressed_key == 'KEY_F1':
                break
                
            draw(1, 1, 20, 'TEST MESSAGE', term.white_on_red, 'TEST')

except KeyboardInterrupt:
    pass
    
finally:
    print(term.normal_cursor(), end='')
    print(term.exit_fullscreen(), end='') 
