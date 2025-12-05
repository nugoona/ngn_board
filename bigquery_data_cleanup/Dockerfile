FROM python:3.11-slim

WORKDIR /app

# requirements.txt 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY test_cleanup.py .

# 실행 (Cloud Run Job은 직접 실행 스크립트)
CMD ["python", "test_cleanup.py"]
