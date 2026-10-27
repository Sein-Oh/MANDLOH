# MANDLOH
만들오의 자료공방 입니다.  
내용은 [블로그]에 담고 있습니다.  
* * *

흩어져 있던 개인 저장소 21개를 이 저장소 하나로 통합했습니다. 파일만 옮겼고 커밋 기록은 각 원본 저장소에 남아 있습니다.  
언어(Python / Javascript)가 아니라 **주제별**로 분류했습니다.

## 폴더 구성
| 폴더 | 내용 | 하위 폴더 |
|---|---|---|
| `01_AI_ML` | 머신러닝·딥러닝 학습과 추론 | `basics`(MLP, 회귀, 데이터 분석), `keras_torch`(Keras·PyTorch 학습), `tfjs`(TensorFlow.js), `tfjs_node`(Node.js 학습·데이터 생성), `browser_ml`(Teachable Machine, ONNX, Pyodide), `models`(학습된 가중치), `object_detection` |
| `02_Vision` | 컴퓨터 비전 (OpenCV, 객체 추적) | `opencv_js`(camshift, meanshift, lk_track, template_matching …), `opencv_py`(yolov4_tiny, cvui, 예제) |
| `03_LLM_Agent` | LLM 클라이언트·에이전트·MCP | `AI_Agent`, `gemma`, `neutralino_client`, `langchain_server`, `langgraph_ui`, `chainlit` |
| `04_GUI` | 화면 UI 프레임워크 | `desktop`(tk, customtkinter, pyside6, eel), `terminal`(textual, blessed, curses, py_cui, cli), `web`(widgets, SimpleSwitch, p5js, streamlit, gradio) |
| `05_Web_Network` | 서버·통신 | `flask`, `socketio`, `python_socket`(tornado, udp, websocket), `WebRTC`, `store` |
| `06_Capture_Automation` | 화면·클립보드 캡처, 자동화 | `js_capture_screen`, `legacy_fabric_capture`, `clipboard`, `stdio`, `win`, `winauto`, `playwright`, `selenium`, `telegram` |
| `07_IoT_MCU` | 마이크로컨트롤러 펌웨어와 웹 제어 페이지 | `ESP32`, `MicroBit`, `Lego_Jeep_RC` |
| `08_Projects` | 완성·진행 중인 프로젝트 | `LinW`(코드·모델·데이터셋 통합), `mandlohto`(만들오토 웹사이트), `tmm` |

## 이전 저장소 위치
| 예전 저장소 | 새 위치 |
|---|---|
| 3D_Modeling | 삭제 |
| MANDLOH-backup | 내용별로 분산: `07_IoT_MCU/ESP32/*`, `07_IoT_MCU/MicroBit/{web_bluetooth,hex}`, `01_AI_ML/tfjs/{UNET,blaze_face}`, `01_AI_ML/keras_torch/{keras,torch}`, `02_Vision/opencv_py/yolov4_tiny`, `04_GUI/desktop/{tk,eel}/legacy_backup`, `06_Capture_Automation/legacy_fabric_capture` |
| microbit-webBLE | `07_IoT_MCU/MicroBit/microbit-webBLE` |
| image_classifier | `01_AI_ML/browser_ml/image_classifier` |
| LK_track | `02_Vision/opencv_js/lk_track` |
| OpencvJS | `02_Vision/opencv_js/OpencvJS_examples` |
| opencvjs_camshift | `02_Vision/opencv_js/camshift` |
| opencvjs_meanshift | `02_Vision/opencv_js/meanshift` |
| opencvjs_gray | `02_Vision/opencv_js/gray` |
| WebRTC_basic | `05_Web_Network/WebRTC/WebRTC_basic` |
| coco_ssd, tfjs-Digit, tiny-yolo, tfjs, tfjs_yolov5.github.io | `01_AI_ML/tfjs/<예전 저장소 이름>` |
| js_capture_screen | `06_Capture_Automation/js_capture_screen` |
| gemma | `03_LLM_Agent/gemma` |
| node | `01_AI_ML/tfjs_node` |
| mandlohto.github.io | `08_Projects/mandlohto` |
| python | 내용별로 분산: `04_GUI/desktop/{eel,tk}`, `05_Web_Network/{flask/legacy,store,WebRTC}`, `01_AI_ML/keras_torch/learning`, `08_Projects/LinW/flask_legacy` |
| Python-learning | 내용별로 분산: `01_AI_ML/keras_torch/learning`, `02_Vision/opencv_py/learning`, `05_Web_Network/python_socket`, `04_GUI/desktop/eel/learning`, `06_Capture_Automation/winauto` |

## 참고 환경 (예전 Python 예제 기준)
* python == 3.8.3rc1
* opencv-python == 4.4.0.46
* torch == 1.7.1

[블로그]:  https://mandloh.tistory.com
