#!/usr/bin/env python3
import subprocess
import sys
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

tests = [
    "test_bot.py",
    "test_http_endpoints.py",
    "test_multi_turn.py",
    "test_generalization.py",
    "test_adversarial.py",
    "test_red_team_audit.py",
    "verify_all_20_stages.py",
    "test_30_pairs.py",
    "validate_final_submission.py"
]

failed = []
for t in tests:
    print(f"\n==================================================")
    print(f"RUNNING {t}...")
    print(f"==================================================")
    res = subprocess.run([sys.executable, t], capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(res.stdout)
    if res.returncode != 0:
        print(f"[FAIL] {t} returned exit code {res.returncode}")
        print(res.stderr)
        failed.append(t)
    else:
        print(f"[PASS] {t} completed successfully.")

if failed:
    print(f"\n[SUMMARY] FAILED SUITES: {failed}")
    sys.exit(1)
else:
    print(f"\n==================================================")
    print(f"ALL {len(tests)} TEST SUITES PASSED WITH ZERO FAILURES!")
    print(f"==================================================")
