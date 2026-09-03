#!/usr/bin/env python3
"""Check run.json status. Exit 1 if not PASS.

Handles both smoke and regression profiles:
- smoke: check tests_* invariants and source_sha_match
- regression: check regression-specific invariants including type validation
- write: check write relay invariants
"""
import json
import os
import sys
import glob


def check_int(value, name):
    """Verify value is a non-negative integer. Exit 1 if not."""
    if value is None or not isinstance(value, int) or value < 0:
        print(f"::error::{name} must be non-negative integer, got {value}")
        return False
    return True


def main():
    rid = os.environ.get("REQUEST_ID", "")
    if not rid:
        rid = f"failed-{os.environ.get('GITHUB_RUN_ID', 'unknown')}"

    path = f"proof/{rid}/run.json"
    if not os.path.exists(path):
        paths = glob.glob("proof/*/run.json")
        if not paths:
            # Try nested proof dirs
            paths = glob.glob("proof/*/*/run.json")
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

    valid = True

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
        
        # Type checks
        for val, name in [(te, "tests_expected"), (tf, "tests_found"), (tx, "tests_executed"),
                          (tp, "tests_passed"), (tfl, "tests_failed"), (tm, "tests_missing")]:
            if not check_int(val, name):
                valid = False
        
        # Invariant checks
        if valid and (tm != 0 or tfl != 0 or tx != te or te == 0 or not sm):
            print(f"::error::Invariant violation in smoke proof")
            valid = False

    # For regression profile, verify all invariants
    elif profile == "regression":
        lost = data.get("lost_count")
        changed = data.get("changed_count")
        base_count = data.get("baseline_exact_count")
        cand_count = data.get("candidate_exact_count")
        
        print(f"  lost={lost} changed={changed} base={base_count} cand={cand_count}")
        
        # Type checks — None/null values are invalid for PASS
        for val, name in [(lost, "lost_count"), (changed, "changed_count"),
                          (base_count, "baseline_exact_count"), (cand_count, "candidate_exact_count")]:
            if not check_int(val, name):
                valid = False
        
        # Invariant checks
        if valid and lost != 0:
            print(f"::error::PASS requires lost_count=0, got {lost}")
            valid = False
        if valid and changed != 0:
            print(f"::error::PASS requires changed_count=0, got {changed}")
            valid = False
        if valid and base_count == 0:
            print(f"::error::baseline_exact_count must be > 0")
            valid = False
        if valid and cand_count < base_count:
            print(f"::error::candidate_exact_count ({cand_count}) < baseline ({base_count})")
            valid = False

    # For write profile — fail-closed invariants (v1.1)
    elif profile == "write":
        push_confirmed = data.get("push_confirmed", False)
        tests = data.get("tests", {}) if isinstance(data.get("tests"), dict) else {}
        tp = tests.get("passed", 0)
        tfl = tests.get("failed", 0)
        te = tests.get("expected", 0)
        tx = tests.get("executed", 0)
        stage = data.get("stage", "")
        base_sha = data.get("base_sha", "")
        actual_base = data.get("actual_base_sha", "")
        files_requested = data.get("files_requested", 0)
        files_changed = data.get("files_changed", [])
        required = data.get("required_checks", [])
        checks_exec = data.get("checks_executed", [])

        def _nonneg_int(val):
            return isinstance(val, int) and not isinstance(val, bool) and val >= 0

        for val, name in [(tp, "tests.passed"), (tfl, "tests.failed"),
                          (te, "tests.expected"), (tx, "tests.executed"),
                          (files_requested, "files_requested")]:
            if not _nonneg_int(val):
                print(f"::error::{name} must be a non-negative integer, got {val!r}")
                valid = False

        if not push_confirmed:
            print(f"::error::PASS requires push_confirmed=true")
            valid = False
        if stage != "pushed":
            print(f"::error::PASS requires stage='pushed', got {stage!r}")
            valid = False
        if tfl != 0:
            print(f"::error::PASS requires tests_failed=0, got {tfl}")
            valid = False
        if te <= 0:
            print(f"::error::PASS requires tests_expected>0, got {te}")
            valid = False
        if tx != te:
            print(f"::error::PASS requires tests_executed==tests_expected "
                  f"({tx} != {te})")
            valid = False
        if "python-tests" in required and "python-tests" not in checks_exec:
            print(f"::error::required check 'python-tests' was not executed")
            valid = False
        if base_sha and actual_base and base_sha != actual_base:
            print(f"::error::base_sha != actual_base_sha")
            valid = False
        if isinstance(files_changed, list) and files_requested > 0 \
                and len(files_changed) != files_requested:
            print(f"::error::files_changed ({len(files_changed)}) != "
                  f"files_requested ({files_requested})")
            valid = False

    if not valid:
        sys.exit(1)

    print("PASS confirmed from run.json")
    sys.exit(0)


if __name__ == "__main__":
    main()
