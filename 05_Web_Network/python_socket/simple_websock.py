from simple_websocket_server import WebSocketServer, WebSocket

class SimpleEcho(WebSocket):
    def handle(self):
        # echo message back to client
        self.send_message(self.data)
        print(self.data)

    def connected(self):
        print(self.address, 'connected')

    def handle_close(self):
        print(self.address, 'closed')


server = WebSocketServer('192.168.0.196', 8000, SimpleEcho)
server.serve_forever()
