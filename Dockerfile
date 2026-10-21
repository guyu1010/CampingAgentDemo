# 基底 image：要跟 CI 的 Python 版本一致
FROM python:3.13-slim

# 容器裡的工作目錄
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# 再複製其餘程式碼
COPY . .

# 啟動指令：要讀 Railway 給的 $PORT，本機沒有時預設用 8000
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]