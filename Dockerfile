FROM python:3.11-slim

# 완전히 새로운 빌드 - 캐시 없음
RUN echo "FRESH_DEPLOY_$(date +%s)" > /build_marker

WORKDIR /app

# 시스템 패키지
RUN apt-get update && apt-get install -y \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 앱 복사
COPY main.py .

# 보안 설정
RUN adduser --system --no-create-home appuser
RUN chown appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/health || exit 1

CMD ["python", "main.py"]