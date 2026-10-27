import numpy as np
import cv2

class App(object):
    def __init__(self, video_src):
        self.cam = cv2.VideoCapture(video_src)
        _ret, self.frame = self.cam.read()
        cv2.namedWindow('camshift')
        cv2.setMouseCallback('camshift', self.onmouse)
        self.track_window = None
        self.selection = None

    def onmouse(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.track_window = None
            self.selection = x-10, y-10, x+10, y+10

        if event == cv2.EVENT_LBUTTONUP:
            self.selection = None
            self.track_window = x-10, y-10, x+10, y+10

    def run(self):
        while True:
            _ret, self.frame = self.cam.read()
            vis = self.frame.copy()
            hsv = cv2.cvtColor(self.frame, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, np.array((0., 60., 32.)), np.array((180., 255., 255.)))

            if self.selection:
                x0, y0, x1, y1 = self.selection
                hsv_roi = hsv[y0:y1, x0:x1]
                mask_roi = mask[y0:y1, x0:x1]
                hist = cv2.calcHist( [hsv_roi], [0], mask_roi, [16], [0, 180] )
                cv2.normalize(hist, hist, 0, 255, cv2.NORM_MINMAX)
                self.hist = hist.reshape(-1)
                vis_roi = vis[y0:y1, x0:x1]
                cv2.bitwise_not(vis_roi, vis_roi)
                vis[mask == 0] = 0

            if self.track_window != None:
                prob = cv2.calcBackProject([hsv], [0], hist, [0, 180], 1)
                prob &= mask
                term_crit = ( cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 1 )
                track_box, self.track_window = cv2.CamShift(prob, self.track_window, term_crit)
                try:
                    cv2.ellipse(vis, track_box, (0, 0, 255), 2)
                except:
                    print(track_box)

            cv2.imshow('camshift', vis)
            key = cv2.waitKey(1) & 0xff
            if key == ord('q'):
                break
            if key == ord('c'):
                self.track_window = None
        cv2.destroyAllWindows()
if __name__ == '__main__':
    App(0).run()
