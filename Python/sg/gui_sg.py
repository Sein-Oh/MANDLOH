
import PySimpleGUI as sg


sg.theme("Default1")
text_size = (12,1)


viewer = [
    [sg.Text("HP:미확인", key="lbl_hp", size=(10, None)), sg.Image(size=(200, 6), key="img_hp")],
]

control = [
    [
        sg.Checkbox("귀환"),
        sg.Text("입력키:"), sg.Input("8", size=(6,None), justification="center"),
        sg.Text("쿨타임:"), sg.Input(0.2, size=(3,None), justification="center"),
        sg.Text("HP범위:"), sg.Input(0.2, size=(6,None), justification="center")
    ],
    [
        sg.Checkbox("귀환"),
        sg.Text("입력키:"), sg.Input("8", size=(6,None), justification="center"),
        sg.Text("쿨타임:"), sg.Input(0.2, size=(3,None), justification="center"),
        sg.Text("HP범위:"), sg.Input(0.2, size=(6,None), justification="center")
    ],
    [
        sg.Checkbox("귀환"),
        sg.Text("입력키:"), sg.Input("8", size=(6,None), justification="center"),
        sg.Text("쿨타임:"), sg.Input(0.2, size=(3,None), justification="center"),
        sg.Text("HP범위:"), sg.Input(0.2, size=(6,None), justification="center")
    ],
    
]

layout = [
    [sg.Frame("모니터링", viewer, expand_x=True)],
    [sg.Frame("제어", control, expand_x=True)],
    [sg.Multiline(size=(20, 5), disabled=True, autoscroll=True, auto_refresh=True, reroute_stdout=True, expand_x=True)]
]

window = sg.Window(
    "Lineage W",
    layout,
    # grab_anywhere=True,
    auto_size_buttons=False,
    default_button_element_size=(8, 1),
    default_element_size=(3, 1),
    use_default_focus=False,
    finalize=True
)


while True:
    event, values = window.read()
    if event == sg.WINDOW_CLOSED:
        break

window.close()