FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Chạy ứng dụng trên cổng 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]