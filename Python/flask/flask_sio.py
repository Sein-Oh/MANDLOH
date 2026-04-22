from flask import Flask, render_template
from flask_socketio import SocketIO
import os
import threading
import time

app = Flask(__name__)
socketio = SocketIO(app, async_mode="threading")


@app.route('/')
def index():
    HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Flask-SocketIO</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
</head>
<body>
	<img id="img">
    <textarea id="area" rows="6" cols="22"></textarea>
</body>
<script>
	let t_prev = Date.now()
	const img = document.getElementById("img")
    const area = document.getElementById('area')
	const socket = io()
	socket.on("connect", () => {
		console.log("connect")
	})
	
	socket.on("time_event", (data) => {
		console.log(data)
        const value = `${data}\n`
        area.append(value)
	})
	
	socket.on("stream", (data) => {
		img.src = `data:image/png;base64,${data.slice(2, -1)}`
		t = Date.now()
		//console.log(t-t_prev)
		t_prev = t
	})
</script>
</html>
    """
    return HTML


def time_sender():
    while True:
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        socketio.emit("time_event", now)
        #print(now)
        time.sleep(1)


@socketio.on('connect')
def handle_connect():
    print('클라이언트가 연결되었습니다.')
    threading.Thread(target=time_sender, daemon=True).start()
    
@socketio.on('disconnect')
def handle_disconnect():
    print('클라이언트가 연결을 종료했습니다.')
    os._exit(1)

@socketio.on('message')
def handle_message(data):
    print('받은 메시지:', data)
    socketio.emit('message', data)


socketio.run(app, host="127.0.0.1", port="8000", debug=True, use_reloader=False)
