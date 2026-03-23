# simulators/run_scenario.py
# ============================================================
# Scenario Orchestrator — Điều phối toàn bộ kịch bản test E2E
# ============================================================
# Chạy kịch bản test theo từng phase, tự động khởi/tắt các simulator.
#
# 3 kịch bản:
#   ddos:             Normal → DDoS flood → Quan sát → Verify recovery
#   organic-overload: Normal → Tải tăng dần → Quan sát → Verify
#   mixed:            Normal → Noise + DDoS đồng thời → Verify Agent phân biệt đúng
#
# Usage:
#   python run_scenario.py --scenario ddos --target http://localhost:8000
#   python run_scenario.py --scenario organic-overload --target http://localhost:8000
#   python run_scenario.py --scenario mixed --target http://localhost:8000
# ============================================================

import argparse
import subprocess
import sys
import time
import os

# Đường dẫn tới thư mục chứa các simulator
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def run_phase(name, duration):
    """In thông báo bắt đầu 1 phase và đợi."""
    print(f"\n{'='*60}")
    print(f"  PHASE: {name} ({duration}s)")
    print(f"{'='*60}")


def start_simulator(script_name, args_list):
    """
    Khởi chạy 1 simulator dưới dạng subprocess (chạy song song).

    Returns: subprocess.Popen object — gọi .terminate() để dừng.
    """
    script_path = os.path.join(SCRIPT_DIR, script_name)
    cmd = [sys.executable, script_path] + args_list
    print(f"  [START] {script_name} {' '.join(args_list)}")
    return subprocess.Popen(cmd)


def wait_and_stop(processes, duration):
    """Đợi `duration` giây rồi terminate tất cả subprocess."""
    time.sleep(duration)
    for p in processes:
        p.terminate()
    for p in processes:
        p.wait()


def scenario_ddos(target, normal_dur=60, attack_dur=120, observe_dur=60, verify_dur=60):
    """
    Kịch bản DDoS:
      Phase 1: Normal traffic            → baseline metrics ổn định
      Phase 2: DDoS flood bùng nổ        → latency tăng vọt, Agent cần detect
      Phase 3: Observation (DDoS tiếp)   → Agent nên chặn IP bằng NetworkPolicy
      Phase 4: Verify                    → latency phải giảm về < 200ms
    """
    # Phase 1: Normal — MQTT devices gửi dữ liệu bình thường
    run_phase("NORMAL TRAFFIC (baseline)", normal_dur)
    mqtt_proc = start_simulator("mqtt_publisher.py", ["--broker", "localhost", "--devices", "5", "--interval", "1"])
    time.sleep(normal_dur)

    # Phase 2: DDoS attack — thêm HTTP flood cùng lúc
    run_phase("DDoS ATTACK", attack_dur)
    ddos_proc = start_simulator("ddos_simulator.py", ["--target", target, "--threads", "10", "--duration", str(attack_dur)])
    time.sleep(attack_dur)

    # Phase 3: Observation — dừng DDoS, xem Agent có chặn không
    run_phase("OBSERVATION (Agent should mitigate)", observe_dur)
    ddos_proc.terminate()
    ddos_proc.wait()
    time.sleep(observe_dur)

    # Phase 4: Verify — dừng tất cả, kiểm tra metrics
    run_phase("VERIFY RECOVERY", verify_dur)
    time.sleep(verify_dur)

    # Cleanup
    mqtt_proc.terminate()
    mqtt_proc.wait()
    print(f"\n{'='*60}")
    print("  SCENARIO ddos COMPLETED")
    print(f"{'='*60}")


def scenario_organic_overload(target, normal_dur=60, ramp_dur=120, observe_dur=60, verify_dur=60):
    """
    Kịch bản Organic Overload:
      Phase 1: Normal traffic
      Phase 2: Noise tăng dần (gradual) — giả lập giờ cao điểm
      Phase 3: Observation — Agent nên scale up (không chặn IP)
      Phase 4: Verify recovery
    """
    run_phase("NORMAL TRAFFIC (baseline)", normal_dur)
    mqtt_proc = start_simulator("mqtt_publisher.py", ["--broker", "localhost", "--devices", "5"])
    time.sleep(normal_dur)

    # Phase 2: Tải tăng dần bằng noise + thêm MQTT devices
    run_phase("ORGANIC OVERLOAD (gradual ramp)", ramp_dur)
    noise_proc = start_simulator("noise_generator.py", ["--target", target, "--rate", "50", "--duration", str(ramp_dur)])
    mqtt_extra = start_simulator("mqtt_publisher.py", ["--broker", "localhost", "--devices", "20", "--interval", "0.5"])
    time.sleep(ramp_dur)

    run_phase("OBSERVATION (Agent should scale up)", observe_dur)
    noise_proc.terminate()
    noise_proc.wait()
    mqtt_extra.terminate()
    mqtt_extra.wait()
    time.sleep(observe_dur)

    run_phase("VERIFY RECOVERY", verify_dur)
    time.sleep(verify_dur)

    mqtt_proc.terminate()
    mqtt_proc.wait()
    print(f"\n{'='*60}")
    print("  SCENARIO organic-overload COMPLETED")
    print(f"{'='*60}")


def scenario_mixed(target, normal_dur=60, mixed_dur=120, observe_dur=60, verify_dur=60):
    """
    Kịch bản Mixed:
      Phase 1: Normal traffic
      Phase 2: Noise + DDoS cùng lúc — Agent cần phân biệt:
               → chặn IP DDoS (uniform + many IPs)
               → KHÔNG chặn noise (few IPs + diverse payload)
      Phase 3-4: Observation + Verify
    """
    run_phase("NORMAL TRAFFIC (baseline)", normal_dur)
    mqtt_proc = start_simulator("mqtt_publisher.py", ["--broker", "localhost", "--devices", "5"])
    time.sleep(normal_dur)

    run_phase("MIXED: Noise + DDoS (Agent must distinguish)", mixed_dur)
    noise_proc = start_simulator("noise_generator.py", ["--target", target, "--rate", "20", "--duration", str(mixed_dur)])
    ddos_proc = start_simulator("ddos_simulator.py", ["--target", target, "--threads", "10", "--duration", str(mixed_dur)])
    time.sleep(mixed_dur)

    run_phase("OBSERVATION", observe_dur)
    noise_proc.terminate()
    ddos_proc.terminate()
    noise_proc.wait()
    ddos_proc.wait()
    time.sleep(observe_dur)

    run_phase("VERIFY RECOVERY", verify_dur)
    time.sleep(verify_dur)

    mqtt_proc.terminate()
    mqtt_proc.wait()
    print(f"\n{'='*60}")
    print("  SCENARIO mixed COMPLETED")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="Scenario Orchestrator")
    parser.add_argument("--scenario", required=True, choices=["ddos", "organic-overload", "mixed"],
                        help="Kịch bản test")
    parser.add_argument("--target", required=True, help="Target URL, vd: http://localhost:8000")
    args = parser.parse_args()

    print(f"[ORCHESTRATOR] Scenario: {args.scenario}")
    print(f"[ORCHESTRATOR] Target: {args.target}")
    print(f"[ORCHESTRATOR] Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    if args.scenario == "ddos":
        scenario_ddos(args.target)
    elif args.scenario == "organic-overload":
        scenario_organic_overload(args.target)
    elif args.scenario == "mixed":
        scenario_mixed(args.target)


if __name__ == "__main__":
    main()
