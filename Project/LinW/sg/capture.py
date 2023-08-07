import cv2
import time
import threading
import dxcam

class Capture:
    def __init__(self, fps=2):
        self.fps = fps
        self.capture_show = False
        self.capture_run = False
        self.camera = dxcam.create(output_color="BGR")
        self.frame = None
        self.start()

    def capture_loop(self):
        self.camera.start(target_fps=self.fps)
        while True:
            if self.capture_run == False:
                return
            self.frame = self.camera.get_latest_frame()
            # self.frame = cv2.resize(self.frame, dsize=(0,0), fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
            time.sleep(1/self.fps)

    def start(self):
        print("캡처를 시작합니다.")
        self.capture_run = True
        threading.Thread(target=self.capture_loop, daemon=True).start()

    def stop(self):
        print("캡처를 중지합니다.")
        self.capture_run = False
        self.camera.stop()
        
    def show_loop(self):
        while True:
            cv2.imshow("frame", self.frame)
            key = cv2.waitKey(1)
            if key == ord("q") or self.show == False:
                print("show loop stopped.")
                cv2.destroyAllWindows()
                return
            
    def show(self):
        print("show loop stop.")
        self.capture_show = True
        threading.Thread(target=self.show_loop, daemon=True).start()

    def hide(self):
        self.capture_show = False