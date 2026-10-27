import requests
import time
import datetime

url = "https://naver.com"
delay = 3
prevRes = requests.get(url).text
time.sleep(delay)

while True:
    currRes = requests.get(url).text
    if currRes != prevRes:
        print("{}-changed".format(datetime.datetime.now()))
    prevRes = currRes
    time.sleep(delay)
