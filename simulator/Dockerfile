# Sử dụng bản Python nhẹ
FROM python:3.9-slim

# Thiết lập thư mục làm việc
WORKDIR /app

# Cài đặt thư viện cần thiết
RUN pip install --no-cache-dir paho-mqtt requests

COPY . .

# CMD mặc định (bạn có thể ghi đè lệnh này trong file k8s deployment)
CMD ["python", "noise_gen.py"]