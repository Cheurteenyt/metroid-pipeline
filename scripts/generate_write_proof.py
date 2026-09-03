#!/usr/bin/env python3
"""Generate the fail-closed proof for a write relay run.

Output: proof/github-write/<request_id>/run.json (schema github-write-proof/v1)

Status semantics (mission GPT 5.6, ETAPES 5 & 9 — no false claims):

  status:
    PASS      patch applied == requested, tests green, push confirmed,
              base SHA verified, stage == pushed
    REJECTED  refused BEFORE any mutation (validation, anti-replay, base SHA)
    FAIL      execution error after acceptance (branch/apply/tests/commit/push)
    UNKNOWN   inconsistent or missing data (fail-closed catch-all)

  stage (what the system can actually prove, monotonically):
    rejected -> validated -> branched -> applied -> tested -> committed -> pushed

PASS is impossible unless EVERY input needed to claim it is present and
consistent. Missing files/envs degrade the status, never upgrade it.
"""
import datetime
import json
import os
import sys
from pathlib import Path

REPOSITORY = "Cheurteenyt/metroid-pipeline"
SOURCE_REPO_GITLAB = "gitlab.com/cheurteen/metroid"


def _load_json(path, default=None):
    if default is None:
        default = {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:  # noqa: BLE001 — proof must never crash
        return default


def _gi(key, default=0):
    """env int, safe."""
    try:
        return int(os.environ.get(key, "").strip() or default)
    except (TypeError, ValueError):
        return default


def _gb(key):
    return os.environ.get(key, "").strip().lower() == "true"


def _gs(key, default=""):
    val = os.environ.get(key, default)
    return val if isinstance(val, str) else default


def build_proof(validation, apply_result, test_result):
    rid = _gs("REQUEST_ID", "unknown")
    stage = _gs("STAGE", "rejected").strip().lower() or "rejected"
    fail_reason = _gs("FAIL_REASON", "")

    base_sha = _gs("BASE_SHA")
    actual_base = _gs("ACTUAL_BASE_SHA")
    result_sha = _gs("RESULT_SHA")
    branch = _gs("TARGET_BRANCH")
    push_confirmed = _gb("PUSH_CONFIRMED")

    # Requested file count (from validation) vs actually applied (from applier)
    requested_count = 0
    if isinstance(validation, dict):
        norm = validation.get("normalized") or {}
        if isinstance(norm, dict):
            requested_count = len(norm.get("files", []))
    applied_count = 0
    files_changed = []
    if isinstance(apply_result, dict):
        applied_count = int(apply_result.get("count", 0) or 0)
        files_changed = list(apply_result.get("applied_paths", []))

    # Tests: prefer the results file, fall back to env counters.
    tests = {
        "expected": _gi("TESTS_EXPECTED"),
        "executed": _gi("TESTS_EXECUTED"),
        "passed": _gi("TESTS_PASSED"),
        "failed": _gi("TESTS_FAILED"),
    }
    if isinstance(test_result, dict) and test_result:
        for k in ("expected", "executed", "passed", "failed"):
            try:
                tests[k] = int(test_result.get(k, tests[k]))
            except (TypeError, ValueError):
                pass

    required_checks = []
    if isinstance(validation, dict):
        norm = validation.get("normalized") or {}
        if isinstance(norm, dict) and isinstance(norm.get("required_checks"), list):
            required_checks = norm["required_checks"]

    checks_executed = []
    if isinstance(test_result, dict):
        ce = test_result.get("checks_executed")
        if isinstance(ce, list):
            checks_executed = ce

    # ------------------------------------------------------------------ status
    # Canonical stages: rejected, validated, branched, applied, tested,
    # committed, pushed. Pre-mutation rejections may arrive under these
    # synonyms; anything unknown degrades to UNKNOWN (fail-closed).
    REJECTED_STAGES = {"rejected", "validation", "anti_replay", "base_sha"}
    FAIL_STAGES = {"validated", "branched", "applied", "tested",
                   "committed", "pushing"}

    tests_ok = (
        tests["expected"] > 0
        and tests["executed"] == tests["expected"]
        and tests["failed"] == 0
        and tests["passed"] == tests["executed"]
    )
    python_tests_required = "python-tests" in required_checks
    python_tests_ok = (
        ("python-tests" in checks_executed) if python_tests_required else True
    )
    base_ok = bool(base_sha) and bool(actual_base) and base_sha == actual_base

    if stage in REJECTED_STAGES:
        status = "REJECTED"
        if stage != "rejected":
            stage = "rejected"
    elif stage == "pushed":
        if (push_confirmed and tests_ok and python_tests_ok and base_ok
                and applied_count == requested_count and requested_count > 0):
            status = "PASS"
        else:
            status = "FAIL"
            if not fail_reason:
                fail_reason = "invariants_violated_at_push"
    elif stage in FAIL_STAGES:
        status = "FAIL"
        if not fail_reason:
            fail_reason = f"run_stopped_at_stage_{stage}"
    else:
        status = "UNKNOWN"
        if not fail_reason:
            fail_reason = f"unknown_stage_{stage}"

    proof = {
        "schema": "github-write-proof/v1",
        "profile": "write",
        "request_id": rid,
        "author_model": _gs("AUTHOR_MODEL"),
        "repository": REPOSITORY,
        "source": _gs("SOURCE", "unknown"),
        "source_repo": (
            SOURCE_REPO_GITLAB if _gs("SOURCE", "") == "gitlab"
            else _gs("SOURCE_REPO", REPOSITORY)
        ),
        "requested_source_commit": _gs("REQUESTED_SOURCE_COMMIT"),
        "source_sha_match": _gb("SOURCE_SHA_MATCH"),
        "request_file_sha256": _gs("REQUEST_SHA256"),
        "base_sha": base_sha,
        "actual_base_sha": actual_base,
        "result_sha": result_sha,
        "branch": branch,
        "operation": _gs("OPERATION"),
        "files_requested": requested_count,
        "files_changed": files_changed,
        "required_checks": required_checks,
        "checks_executed": checks_executed,
        "tests": tests,
        "push_confirmed": push_confirmed,
        "stage": stage,
        "status": status,
        "fail_reason": fail_reason,
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc)
        .isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
    return proof


def main(argv):
    args = list(argv[1:])

    def opt(name, default=None):
        if name in args:
            i = args.index(name)
            return args[i + 1]
        return default

    out_path = opt("--output", "")
    validation = _load_json(opt("--validation-json", "/tmp/validation.json"))
    apply_result = _load_json(opt("--apply-json", "/tmp/apply_result.json"))
    test_result = _load_json(opt("--test-json", "/tmp/test_results.json"))

    proof = build_proof(validation, apply_result, test_result)

    rid = proof["request_id"] or "unknown"
    if not out_path:
        out_path = f"proof/github-write/{rid}/run.json"
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(proof, fh, indent=2)
        fh.write("\n")

    print(json.dumps(proof, indent=2))
    print(f"\nproof written: {path}")
    print(f"FINAL STATUS: {proof['status']} (stage: {proof['stage']})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
