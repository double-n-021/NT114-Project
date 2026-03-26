# Sử dụng bản Python nhẹ
FROM python:3.9-slim

# Thiết lập thư mục làm việc
WORKDIR /app

# Cài đặt thư viện cần thiết
RUN pip install --no-cache-dir paho-mqtt

# Copy mã nguồn vào container
COPY mqtt_publisher.py .

# Chạy script
CMD ["python", "mqtt_publisher.py"]