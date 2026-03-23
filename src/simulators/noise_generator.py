# simulators/noise_generator.py
# ============================================================
# EXTERNAL TRAFFIC SOURCE — Noise Generator (PRIORITY: LOW)
# ============================================================
# Giả lập traffic nền không quan trọng: cập nhật hệ thống, video, báo cáo.
# Traffic này cạnh tranh bandwidth với dữ liệu sinh hiệu (MQTT).
#
# Khác biệt so với DDoS:
#   - Ít source IP hơn (1-3 IPs cố định, không random)
#   - Tốc độ tăng dần (gradual), không spike đột ngột
#   - Payload đa dạng (không uniform như DDoS)
#   → Agent cần phân biệt noise vs DDoS để không chặn nhầm
#
# Usage:
#   python noise_generator.py --target http://localhost:8000 --rate 10 --duration 120
# ============================================================

import argparse
import random
import time
import threading
import requests


# Dữ liệu đa dạng — noise traffic không uniform như DDoS
NOISE_PAYLOADS = [
    {"type": "system_update", "version": "2.1.3", "size_kb": 1024},
    {"type": "video_stream", "resolution": "720p", "bitrate": 2500},
    {"type": "report_export", "format": "pdf", "pages": 15},
    {"type": "backup_sync", "files": 42, "total_mb": 256},
    {"type": "log_upload", "entries": 1000, "source": "syslog"},
]

# Ít IP cố định — organic traffic đến từ vài nguồn quen thuộc
FIXED_IPS = ["10.0.50.1", "10.0.50.2", "10.0.50.3"]


def noise_thread(target_url, rate, duration):
    """
    Gửi traffic nền với tốc độ cố định (rate requests/giây).

    Đặc điểm organic noise (để Agent không nhầm với DDoS):
      - IP cố định từ FIXED_IPS (ít diversity)
      - Payload random từ NOISE_PAYLOADS (đa dạng nội dung)
      - Tốc độ ổn định, không spike
    """
    interval = 1.0 / rate  # thời gian giữa 2 requests
    end_time = time.time() + duration
    sent = 0

    while time.time() < end_time:
        payload = random.choice(NOISE_PAYLOADS).copy()
        payload["timestamp"] = time.time()
        headers = {"X-Forwarded-For": random.choice(FIXED_IPS)}

        try:
            resp = requests.post(f"{target_url}/collect", json=payload, headers=headers, timeout=2)
            sent += 1
            if sent % 50 == 0:
                print(f"  [NOISE] Sent {sent} requests @ {rate} req/s")
        except (requests.Timeout, requests.ConnectionError):
            pass

        time.sleep(interval)

    print(f"  [NOISE] Finished. Total sent: {sent}")


def main():
    parser = argparse.ArgumentParser(description="Noise Traffic Generator (Low Priority)")
    parser.add_argument("--target", required=True, help="Target URL, vd: http://localhost:8000")
    parser.add_argument("--rate", type=float, default=10, help="Requests/giây (default: 10)")
    parser.add_argument("--duration", type=int, default=120, help="Thời gian chạy giây (default: 120)")
    args = parser.parse_args()

    print(f"[NOISE] Target: {args.target}")
    print(f"[NOISE] Rate: {args.rate} req/s, Duration: {args.duration}s")
    print(f"[NOISE] Source IPs: {FIXED_IPS} (cố định, ít diversity)")
    print("=" * 60)

    noise_thread(args.target, args.rate, args.duration)

    print("=" * 60)
    print("[NOISE] Done.")


if __name__ == "__main__":
    main()
