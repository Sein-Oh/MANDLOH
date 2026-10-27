import tornado.ioloop
import tornado.web
import tornado.websocket

class MainHandler(tornado.web.RequestHandler):
	def get(self):
		self.render("index.html")

class WebSocket(tornado.websocket.WebSocketHandler):
	def open(self):
		print("WS opened.")
		self.write_message("WS opened from python")

	def on_message(self, msg):
		print(msg)

	def on_close(self):
		print("WS closed.")

def make_app():
	return tornado.web.Application([
		(r"/", MainHandler),
		(r"/ws", WebSocket)
		])

if __name__ == "__main__":
	app = make_app()
	app.listen(8080)
	tornado.ioloop.IOLoop.current().start()
