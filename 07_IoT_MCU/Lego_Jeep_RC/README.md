# MANDLOH
만들오의 자료공방 입니다.
내용은 [블로그]에 담고 있습니다.  
* [코드관련]
* [3D 프린팅 부품관련]
* * *
## 1. ESP32 보드 설치(기존 설치 시 생략 가능)
  1. 아두이노 IDE 환경설정에서 추가적인 보드 매니저 URLs 다음 주소 입력  
    https://dl.espressif.com/dl/package_esp32_index.json
  1. 툴 -> 보드 -> 보드매니저 에서 esp32 검색 후 설치 (다소 시간이 걸리는 경우가 있음)
  
## 2. ESP CAM 스케치 업로드
  - 툴 -> 보드 -> "WSP32 Wrover Module" 선택  
  - 툴 -> Upload Speed : "921600" 선택(권장)  
  - 툴 -> Partition Scheme : "Huge App (3MB No OTA/1MB SPIFFS)" 선택 
  - 업로드 모드로 설정 : IO0 핀과 GND 연결
  - 업로드 중 Connecting .... 에서 시간이 오래걸리면 리셋버튼을 눌러볼 

## 3. Websocket 라이브러리 설치
  1. 다음 주소에서 AsyncTCP 설치  
  https://github.com/me-no-dev/AsyncTCP  
  1. 다음 주소에서 ESPAsyncWebserver 설치  
  https://github.com/me-no-dev/ESPAsyncWebServer  
  1. 라이브러리 설치방법 : Github에서 zip 파일로 내려받은 후, 스케치 -> 라이브러리 포함하기 -> .ZIP 라이브러리  
  
[블로그]:  https://mandloh.tistory.com
[코드관련]: https://mandloh.tistory.com/31
[3D 프린팅 부품관련]: https://mandloh.tistory.com/33
