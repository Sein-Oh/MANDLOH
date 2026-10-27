import onnxruntime as ort
import numpy as np
import cv2

# 1. ONNX 모델 로드
model_path = "train3_best.onnx"
session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])

# 2. 입력 이름과 출력 이름 확인
input_name = session.get_inputs()[0].name
output_name = session.get_outputs()[0].name
print("Input name:", input_name)
print("Output name:", output_name)

# 3. 이미지 불러오기 및 전처리
image_path = "normal.jpg"
img = cv2.imread(image_path)

# YOLO 분류 모델의 기본 입력 크기는 224x224 (yolo11-cls 기준)
img_resized = cv2.resize(img, (224, 224))

# BGR → RGB, float32 변환 및 정규화 (0~1)
img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
img_normalized = img_rgb.astype(np.float32) / 255.0

# (H, W, C) → (1, C, H, W)
input_tensor = np.transpose(img_normalized, (2, 0, 1))[np.newaxis, :, :, :]

# 4. 추론 실행
outputs = session.run([output_name], {input_name: input_tensor})
logits = outputs[0][0]  # (num_classes,)

# 5. 결과 처리
pred_class = np.argmax(logits)
confidence = float(np.max(np.exp(logits) / np.sum(np.exp(logits))))  # softmax로 확률 추정

print(f"예측 클래스 인덱스: {pred_class}")
print(f"신뢰도(Confidence): {confidence:.4f}")