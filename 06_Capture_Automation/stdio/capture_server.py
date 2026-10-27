import sys
import struct
import cv2
import dxcam

def main():
    # 디버그 로그는 반드시 stderr로 출력 (stdout은 이미지 바이너리 전용)
    sys.stderr.write("[Server] Initializing dxcam...\n")
    sys.stderr.flush()

    camera = dxcam.create()
    camera.start(target_fps=60)

    sys.stderr.write("[Server] dxcam is ready! Waiting for commands...\n")
    sys.stderr.flush()

    try:
        # stdin 입력을 줄 단위로 계속 대기 (Blocking)
        for line in sys.stdin:
            cmd = line.strip()

            if cmd == "CAPTURE":
                # 최신 프레임 가져오기
                frame = camera.get_latest_frame()

                if frame is not None:
                    # RGB -> BGR 변환 및 JPEG 압축
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    success, buffer = cv2.imencode('.jpg', frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 80])

                    if success:
                        jpg_bytes = buffer.tobytes()
                        length = len(jpg_bytes)

                        # 1. 4바이트 길이 패킹 헤더 전송 (빅엔디안 정수)
                        sys.stdout.buffer.write(struct.pack('>I', length))
                        # 2. JPEG 이미지 바이너리 전송
                        sys.stdout.buffer.write(jpg_bytes)
                        # 3. 즉시 전송 (버퍼 비우기)
                        sys.stdout.buffer.flush()

            elif cmd == "EXIT":
                sys.stderr.write("[Server] Exit command received.\n")
                sys.stderr.flush()
                break

    except Exception as e:
        sys.stderr.write(f"[Server Error] {e}\n")
        sys.stderr.flush()
    finally:
        camera.stop()
        sys.stderr.write("[Server] Stopped.\n")
        sys.stderr.flush()

if __name__ == '__main__':
    main()