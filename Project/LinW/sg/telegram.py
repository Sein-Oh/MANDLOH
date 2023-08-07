import requests

class Tele:
    def __init__(self, token, id):
        self.token = token
        self.id = id
    
    def send_message(self, msg):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage?chat_id={self.id}&text={msg}"
        requests.get(url)

    def send_photo(self, imgPath, caption):
        data = {"chat_id": self.id, "caption": caption}
        url = f"https://api.telegram.org/bot{self.token}/sendphoto?chat_id={self.id}"
        with open(imgPath, "rb") as f:
            requests.post(url, data=data, files={"photo": f})