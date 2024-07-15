from flask import Flask, Response
from flask_cors import CORS
import time
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)


def generator(user_id):
    #yield f"data: Hello! {user_id}\n\n"
    while True:
        clock = datetime.now().time()
        t = f"{clock:%T}"
        data = {"name": user_id, "time": t}
        yield f"""event: notice\ndata: {json.dumps(data)}\n\n"""
        print("Sent")
        time.sleep(0.5)

@app.get("/connection/<user_id>")
def connection(user_id: str):
    return Response(generator(user_id), content_type="text/event-stream")

if __name__ == "__main__":
    app.run(port=5000)
