import datetime
from blessed import Terminal
import time
import os

def read_txt(path):
    with open(path, "r", encoding="UTF-8") as file:
        raw_file = file.readlines()
        file = list(map(lambda s: s.strip(), raw_file))
        file = [f for f in file if f] #빈칸 제거용
        return file
    

def convert_data(data_path):
    result = {}
    for data in read_txt(data_path):
        title, value = list(map(lambda s: s.strip(), data.split(":")))
        result[title] = value
    return result


def convert_app_data(data_path):
    result = {}
    for data in read_txt(data_path):
        d = list(map(lambda s: s.strip(), data.split(":")))
        if len(d) > 2:
            temp = ""
            for i in range(1, len(d)):
                temp += d[i] + ":"
            title = d[0]
            value = temp[:-1]
        else:
            title, value = d
        result[title] = value
    return result


def clear():
    print(term.clear())
    print(term.snow("~"*term.width))
    with term.location(0, 2+len(slot.keys())):
        print(term.snow("~"*term.width))

app_data = convert_app_data("app.txt")
fps_result = 0

slot = {}
txt_ary = [j for j in os.listdir("data") if ".txt" in j]
for txt in txt_ary:
    name = txt.split(".")[0]
    slot[name] = convert_data(f"data/{txt}")
    slot[name]["cooling"] = False
    slot[name]["run"] = False
    slot[name]["value"] = None


term = Terminal()
clear()
tp = time.time()
with term.cbreak(), term.hidden_cursor():
  while True:
    with term.location(0,0):
      now = datetime.datetime.now()
      print(term.snow(f"{now.strftime('%H:%M:%S')}  FPS:{str(fps_result).ljust(2)}  CAPTURE:{app_data['capture']}  ARDUINO:{app_data['arduino port']}  RESIZE:{app_data['resize']}"))

    with term.location(0,2):
      for idx, name in enumerate(slot.keys()):
        run = term.lawngreen("ON ") if slot[name]['run'] else term.red("OFF")
        value = term.blue(str(slot[name]["value"]))
        # key = slot[name]["key"]
        if slot[name]["type"] == "timer":
            info = f" {idx+1}) {name[:6].ljust(6)}  RUN:{run}"
        elif slot[name]["type"] == "hp":
            info = f" {idx+1}) {name[:6].ljust(6)}  RUN:{run}  VALUE:{str(value).ljust(3)}  RANGE:{slot[name]['min range']}~{slot[name]['max range']}"
        elif slot[name]["type"] == "img":
            info = f" {idx+1}) {name[:6].ljust(6)}  RUN:{run}  VALUE:{str(value).ljust(4)}  THRESHOLD:{slot[name]['threshold']}"
        print(info)


    for name in slot.keys():
        if slot[name]["type"] == "timer":
            if slot[name]["run"] == True:
                if slot[name]["cooling"] == False:
                    key = slot[name]["key"]
                    cooltime = float(slot[name]["cooltime"])

        elif slot[name]["type"] == "hp":
            if slot[name]["run"] == True:
                key = slot[name]["key"]
                cooltime = float(slot[name]["cooltime"])
                x1 = int(slot[name]["x1"])
                y1 = int(slot[name]["y1"])
                x2 = int(slot[name]["x2"])
                y2 = int(slot[name]["y2"])
                thres = float(slot[name]["threshold"])
                min_hp = int(slot[name]["min range"])
                max_hp = int(slot[name]["max range"])

        elif slot[name]["type"] == "img":
            if slot[name]["run"] == True:
                key = slot[name]["key"]
                cooltime = float(slot[name]["cooltime"])
                x1 = int(slot[name]["x1"])
                y1 = int(slot[name]["y1"])
                x2 = int(slot[name]["x2"])
                y2 = int(slot[name]["y2"])
                thres = float(slot[name]["threshold"])

    val = term.inkey(timeout=0)
    key = val.name if val.is_sequence else val

    if key == "q":
      print(term.clear())
      break
    elif key == "0":
      for name in slot.keys():
        slot[name]['run'] = False

    elif key == "c": clear()

    try:
      num = int(key)
      for idx, name in enumerate(slot.keys()):
        if num == idx+1:
          slot[name]['run'] = not slot[name]['run']
    except: pass 
    