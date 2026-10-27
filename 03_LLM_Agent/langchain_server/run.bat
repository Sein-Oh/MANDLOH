@echo off
echo ============================================================
echo  Starting LangChain + FastAPI OpenAI-Compatible Server
echo  LM Studio Target: http://192.168.45.146:1234
echo ============================================================

REM 패키지 설치 확인 (필요 시)
REM pip install -r requirements.txt

python main.py
pause
