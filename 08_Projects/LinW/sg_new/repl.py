import PySimpleGUI as sg

f1 = [
    [sg.Multiline(size=(None, 5), disabled=True, reroute_stdout=True, auto_refresh=True, autoscroll=True)],
    [sg.Input(size=(None, 1), expand_x=True, key="input"), sg.Button("Submit", key="submit")]
]

layout = [
    [sg.Frame("Controll", f1, key="frame")]
]

window = sg.Window("Controller", layout, finalize=True)
window["input"].bind("<Return>", "submit")

while True:
    event, values = window.read()
    if event == sg.WINDOW_CLOSED:
        break
    elif "submit" in event:
        cmd = window["input"].get()
        print(f">>> {cmd}")
        try:
            result = eval(cmd)
        except Exception as e:
            try:
                result = exec(cmd)
            except Exception as e:
                result = e
        if result is not None: print(result)
        window["input"].update("")


window.close()
