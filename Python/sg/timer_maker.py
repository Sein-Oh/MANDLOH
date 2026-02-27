import FreeSimpleGUI as sg
import os
import json

script_path = os.path.dirname(__file__)


layout = [
    [sg.Text('Key', size=(12, None)), sg.Input('', key='key')],
    [sg.Text('Cooltime', size=(12, None)), sg.Input('', key='cooltime')],
    [sg.Button("Clear", key="clear"), sg.Button('save', key='save')]
]

window = sg.Window("Timer maker", layout, finalize=True)

while True:
    event, value = window.read()
    print(event)
    if event == sg.WINDOW_CLOSED:
        break
    
    elif event == 'save':
        filename = sg.tk.filedialog.asksaveasfilename(
            defaultextension='json',
            filetypes=(("JSON Files", "*.json"), ("All Files", "*.*")),
            initialdir=script_path,
            parent=window.TKroot,
            title="Save As"
        )
        key = window['key'].get()
        cooltime = window['cooltime'].get()
        data = {'key' : key, 'cooltime' : cooltime}
        with open(filename, 'w') as f:
            json.dump(data, f)
    
    elif event == 'clear':
        window['key'].update('')
        window['cooltime'].update('')
        

window.close()
