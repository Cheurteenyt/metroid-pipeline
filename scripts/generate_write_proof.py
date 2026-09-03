#!/usr/bin/env python3
"""Generate proof for a write relay operation."""
import json
import os
import sys
import datetime
from pathlib import Path

def main():
    rid = os.environ.get("REQUEST_ID", "unknown")
    proof_dir = Path(f"proof/github-write/{rid}")
    proof_dir.mkdir(parents=True, exist_ok=True)
    
    def gi(k, d=0):
        try: return int(os.environ.get(k, str(d)))
        except: return d
    def ge(k, d=""): return os.environ.get(k, d)
    
    status = "FAIL"
    if (gi("TESTS_PASSED") > 0 and gi("TESTS_FAILED") == 0 
        and ge("PUSH_CONFIRMED") == "true"):
        status = "PASS"
    elif gi("TESTS_EXECUTED") == 0:
        status = "UNKNOWN"
    
    data = {
        "schema": "github-write-proof/v1",
        "request_id": rid,
        "author_model": ge("AUTHOR_MODEL"),
        "repository": "Cheurteenyt/metroid-pipeline",
        "base_sha": ge("BASE_SHA"),
        "actual_base_sha": ge("ACTUAL_BASE_SHA"),
        "result_sha": ge("RESULT_SHA", ""),
        "branch": ge("TARGET_BRANCH"),
        "files_changed": json.loads(ge("FILES_CHANGED", "[]")),
        "tests": {
            "expected": gi("TESTS_EXPECTED"),
            "executed": gi("TESTS_EXECUTED"),
            "passed": gi("TESTS_PASSED"),
            "failed": gi("TESTS_FAILED"),
        },
        "push_confirmed": ge("PUSH_CONFIRMED") == "true",
        "status": status,
        "fail_reason": ge("FAIL_REASON", ""),
        "timestamp_utc": datetime.datetime.utcnow().isoformat() + "Z",
    }
    
    with open(proof_dir / "run.json", "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    
    print(json.dumps(data, indent=2))
    print(f"\n{'='*50}")
    print(f"FINAL STATUS: {status}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
