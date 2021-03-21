import cv2
import numpy as np

width, height = 416, 416
cap = cv2.VideoCapture('mb.mp4')

CONF_THRESH, NMS_THRESH = 0.5, 0.5

net = cv2.dnn.readNetFromDarknet("custom-yolov4-tiny-detector.cfg", "custom-yolov4-tiny-detector_best.weights")
#layers = net.getLayerNames()
#output_layers = [layers[i[0] - 1] for i in net.getUnconnectedOutLayers()]
output_layers = [net.getLayerNames()[i[0] - 1] for i in net.getUnconnectedOutLayers()]

while True:
    ret, img = cap.read()
    img = cv2.resize(img, dsize=(width, height), interpolation=cv2.INTER_AREA)
    blob = cv2.dnn.blobFromImage(img, 0.00392, (416, 416), swapRB=True, crop=False)
    net.setInput(blob)
    layer_outputs = net.forward(output_layers)

    class_ids, confidences, b_boxes = [], [], []
    for output in layer_outputs:
        for detection in output:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]

            if confidence > CONF_THRESH:
                center_x, center_y, w, h = (detection[0:4] * np.array([width, height, width, height])).astype('int')

                x = int(center_x - w / 2)
                y = int(center_y - h / 2)

                b_boxes.append([x, y, int(w), int(h)])
                confidences.append(float(confidence))
                class_ids.append(int(class_id))

    with open("obj.names", "r") as f:
        classes = [line.strip() for line in f.readlines()]

    if len(b_boxes) > 0:
        indices = cv2.dnn.NMSBoxes(b_boxes, confidences, CONF_THRESH, NMS_THRESH).flatten().tolist()
        for index in indices:
            x, y, w, h = b_boxes[index]
            cv2.rectangle(img, (x, y), (x + w, y + h), (255,255,255), 2)
            cv2.putText(img, classes[class_ids[index]], (x + 5, y + 20), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (255,255,255), 2)


    cv2.imshow("image", img)
    key = cv2.waitKey(1)
    if key == ord('q'):
        break
cv2.destroyAllWindows()