import argparse
import time
import requests

parser = argparse.ArgumentParser()
parser.add_argument("--key", nargs="*", type=str, required=True)
parser.add_argument("--cooltime", nargs=None, type=float, required=True)
parser.add_argument("--input_url", nargs=None, type=str, required=True)
args = parser.parse_args()

input_url = args.input_url
if "http://" not in input_url:
    input_url = "http://" + input_url

key = args.key
cooltime = args.cooltime

while True:
    for k in key:
        if "-" in k:
            t = float(k[1:])
            time.sleep(t)
        else:
            try:
                requests.get(f"{input_url}/{k}", timeout=0.2)
            except requests.exceptions.Timeout:
                print(f"Input server is not responding. Key: {k}")
    time.sleep(cooltime)
