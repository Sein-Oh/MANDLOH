import sys
import subprocess
import struct
import time
import cv2
import numpy as np

def read_exact(stream, num_bytes):
    """지정한 바이트 수만큼 정확히 읽어오는 헬퍼 함수"""
    buf = bytearray()
    while len(buf) < num_bytes:
        chunk = stream.read(num_bytes - len(buf))
        if not chunk:
            return None
        buf.extend(chunk)
    return bytes(buf)

def main():
    print("[Client] Starting capture server process...")

    # 파이썬 서버 프로세스를 자식 프로세스(std 파이프 연결)로 실행
    server_process = subprocess.Popen(
        [sys.executable, 'capture_server.py'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,  # 서버의 에러 로그를 클라이언트 터미널에 그대로 표시
        text=False          # 바이너리 통신 모드
    )

    # 서버 초기화 대기 (dxcam 로딩 시간)
    time.sleep(1.5)

    def request_one_frame():
        """서버에 캡처 명령을 보내고 1프레임을 받아오는 함수"""
        # 1. CAPTURE 명령 전송
        server_process.stdin.write(b"CAPTURE\n")
        server_process.stdin.flush()

        # 2. 응답 헤더 (4바이트 크기) 읽기
        header = read_exact(server_process.stdout, 4)
        if not header:
            return None
        
        frame_size = struct.unpack('>I', header)[0]

        # 3. 이미지 바이너리 읽기
        jpg_bytes = read_exact(server_process.stdout, frame_size)
        if not jpg_bytes:
            return None

        # 4. JPEG 디코딩 -> OpenCV 이미지 객체 변환
        nparr = np.frombuffer(jpg_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img

    try:
        print("\n==========================================")
        print(" [Enter] 키 : 원하는 타이밍에 캡처 1회 요청")
        print(" [q] 입력 후 [Enter] : 프로그램 종료")
        print("==========================================\n")

        while True:
            user_input = input(">> 명령 입력: ")

            if user_input.strip().lower() == 'q':
                # 서버에 종료 명령 전송
                server_process.stdin.write(b"EXIT\n")
                server_process.stdin.flush()
                break

            # 엔터 입력 시 캡처 요청 실행
            start_time = time.time()
            img = request_one_frame()
            elapsed_ms = (time.time() - start_time) * 1000

            if img is not None:
                print(f" -> 캡처 성공! (응답 속도: {elapsed_ms:.2f}ms, 이미지 해상도: {img.shape[1]}x{img.shape[0]})")
                # 캡처한 이미지를 창으로 보여줌
                cv2.imshow("On-Demand Capture", img)
                cv2.waitKey(1)
            else:
                print(" -> 캡처 실패 또는 데이터 수신 오류")

    finally:
        print("[Client] Terminating server process...")
        server_process.terminate()
        server_process.wait()
        cv2.destroyAllWindows()
        print("[Client] Done.")

if __name__ == '__main__':
    main()
