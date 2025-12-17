# Python 3.11-slim 이미지 사용
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 필요한 패키지 설치
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 필요한 파일 복사
COPY ngn_wep/cafe24_api/token_refresh.py /app/token_refresh.py

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1

# 토큰 갱신 실행
ENTRYPOINT ["python3", "/app/token_refresh.py"]
