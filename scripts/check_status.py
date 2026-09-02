#!/usr/bin/env python3
"""Check run.json status. Exit 1 if not PASS.

Handles both smoke and regression profiles:
- smoke: check tests_* invariants
- regression: check regression-specific invariants
"""
import json
import os
import sys
import glob

def main():
    rid = os.environ.get("REQUEST_ID", "")
    if not rid:
        rid = f"failed-{os.environ.get('GITHUB_RUN_ID', 'unknown')}"

    path = f"proof/{rid}/run.json"
    if not os.path.exists(path):
        paths = glob.glob("proof/*/run.json")
        if not paths:
            print(f"::error::No run.json found at {path}")
            sys.exit(1)
        path = paths[0]

    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"::error::Invalid JSON in {path}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"::error::Cannot read {path}: {e}")
        sys.exit(1)

    status = data.get("status", "FAIL")
    profile = data.get("profile", "smoke")
    
    print(f"run.json status: {status} (profile: {profile})")
    print(f"  request_id: {data.get('request_id', 'N/A')}")

    if status != "PASS":
        reason = data.get("fail_reason", data.get("reason", "unknown"))
        print(f"::error::Status is {status} (reason: {reason})")
        sys.exit(1)

    # For smoke profile, verify test invariants
    if profile == "smoke":
        te = data.get("tests_expected", 0)
        tf = data.get("tests_found", 0)
        tx = data.get("tests_executed", 0)
        tp = data.get("tests_passed", 0)
        tfl = data.get("tests_failed", 0)
        tm = data.get("tests_missing", 0)
        sm = data.get("source_sha_match", False)
        
        print(f"  tests: expected={te} found={tf} executed={tx} passed={tp} failed={tfl} missing={tm}")
        print(f"  source_sha_match: {sm}")
        
        # Verify invariants
        if tm != 0 or tfl != 0 or tx != te or te == 0 or not sm:
            print(f"::error::Invariant violation in smoke proof")
            sys.exit(1)

    # For regression profile, verify regression invariants
    elif profile == "regression":
        lost = data.get("lost_count", -1)
        changed = data.get("changed_count", -1)
        if lost != 0 or changed != 0:
            print(f"::error::Regression invariant violation: lost={lost} changed={changed}")
            sys.exit(1)

    print("PASS confirmed from run.json")
    sys.exit(0)

if __name__ == "__main__":
    main()
