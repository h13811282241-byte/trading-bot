# Dockerfile
ARG BASE=python:3.11-slim
FROM ${BASE}

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY liangxi_binance_live.py notifier.py ./
ENV TZ=Asia/Shanghai

CMD ["python", "liangxi_binance_live.py"]
