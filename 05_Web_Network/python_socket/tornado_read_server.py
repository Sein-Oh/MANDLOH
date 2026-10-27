import tornado.ioloop
import tornado.web
import tornado.websocket
import base64
import numpy as np
import cv2
import warnings
warnings.simplefilter("ignore", DeprecationWarning)
import threading

class MainHandler(tornado.web.RequestHandler):
	def get(self):
		self.render("tornado_read_index.html")

class WebSocket(tornado.websocket.WebSocketHandler):
	def open(self):
		print("WS opened.")
		self.write_message("WS opened from python")

	def on_message(self, msg):
		print(msg[0:10])
		draw(msg)
		
	def on_close(self):
		print("WS closed.")

def make_app():
	return tornado.web.Application([
		(r"/", MainHandler),
		(r"/static/(.*)",tornado.web.StaticFileHandler, {"path": "./static"},),
		(r"/ws", WebSocket)
		])
		
def draw(msg):
	img = cv2.imdecode(np.fromstring(base64.b64decode(msg.split(',')[1]), np.uint8), cv2.IMREAD_COLOR)
	cv2.imshow('img', img)
	cv2.waitKey(60)
	
if __name__ == "__main__":
	app = make_app()
	app.listen(8080)
	tornado.ioloop.IOLoop.current().start()
