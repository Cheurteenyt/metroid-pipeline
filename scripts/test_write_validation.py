#!/usr/bin/env python3
"""Adversarial + positive tests for the github-write-request/v1 relay chain.

Covers (mission GPT 5.6, ETAPE 7 — each rejection path must imply NO PUSH):

  - validator: schema, ids, repo, model, SHA, paths (traversal/absolute/
    bare '..', denylist, allowlist chars), sizes, duplicates, operations,
    commit prefix, required_checks fail-closed, malformed JSON
  - apply_write_patch: patch/create/delete semantics, symlink escapes,
    missing/existing file rules
  - generate_write_proof: status matrix (PASS/REJECTED/FAIL/UNKNOWN) —
    PASS only in the exact full-success condition
  - check_status.py (write profile): fail-closed invariants via subprocess

Runs under pytest OR standalone (`python3 scripts/test_write_validation.py`).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from validate_write_request import validate  # noqa: E402

VALID_BASE = {
    "schema": "github-write-request/v1",
    "request_id": "test-001",
    "target_repo": "Cheurteenyt/metroid-pipeline",
    "target_branch": "advisory/branch",
    "base_sha": "a" * 40,
    "author_model": "GLM 5.2",
    "operation": "patch",
    "files": [{"path": "docs/test.md", "patch": "# test\n"}],
    "commit_message": "[GLM-5.2] test commit",
    "required_checks": ["python-tests"],
}

RESULTS = []


def make_request(**overrides):
    req = dict(VALID_BASE)
    for k, v in overrides.items():
        if v is None:
            req.pop(k, None)
        else:
            req[k] = v
    return req


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(f"{'PASS' if cond else 'FAIL'}: {name}"
          + (f" — {detail}" if (detail and not cond) else ""))
    return bool(cond)


# ---------------------------------------------------------------------------
# 1. Validator — negative cases (each must be REJECTED)
# ---------------------------------------------------------------------------

def _neg(name, request, needle=None):
    valid, errors, _ = validate(request)
    ok = not valid
    if ok and needle:
        ok = any(needle.lower() in e.lower() for e in errors)
    return check(f"validator rejects: {name}", ok, str(errors[:2]))


def test_validator_negatives():
    _neg("bad schema", make_request(schema="wrong"))
    _neg("empty request_id", make_request(request_id=""))
    _neg("non-string request_id", make_request(request_id=123))
    _neg("reserved request_id", make_request(request_id="unknown"))
    _neg("request_id with slash", make_request(request_id="a/b"))
    _neg("wrong repo", make_request(target_repo="evil/repo"))
    _neg("SHA 39 chars", make_request(base_sha="a" * 39))
    _neg("SHA non-hex", make_request(base_sha="g" * 40))
    _neg("SHA uppercase", make_request(base_sha="A" * 40))
    _neg("SHA non-string", make_request(base_sha=12345))
    _neg("path traversal ../", make_request(
        files=[{"path": "../evil.py", "patch": "x"}]))
    _neg("bare dotdot path", make_request(files=[{"path": "..", "patch": "x"}]))
    _neg("nested traversal a/../../x", make_request(
        files=[{"path": "a/../../x", "patch": "x"}]))
    _neg("absolute path", make_request(
        files=[{"path": "/etc/passwd", "patch": "x"}]))
    _neg("windows absolute", make_request(
        files=[{"path": "C:/evil", "patch": "x"}]))
    _neg("backslash path", make_request(
        files=[{"path": "a\\b\\evil", "patch": "x"}]))
    _neg("workflow file", make_request(
        files=[{"path": ".github/workflows/evil.yml", "patch": "x"}]))
    _neg(".github non-workflow", make_request(
        files=[{"path": ".github/CODEOWNERS", "patch": "x"}]))
    _neg("secret file", make_request(
        files=[{"path": "secrets/token.key", "patch": "x"}]))
    _neg(".env file", make_request(files=[{"path": ".env", "patch": "x"}]))
    _neg(".env.local", make_request(
        files=[{"path": "config/.env.local", "patch": "x"}]))
    _neg("pem file", make_request(files=[{"path": "cert.pem", "patch": "x"}]))
    _neg("key file", make_request(files=[{"path": "k.key", "patch": "x"}]))
    _neg("gitmodules", make_request(
        files=[{"path": ".gitmodules", "patch": "x"}]))
    _neg("gitlab-ci", make_request(
        files=[{"path": ".gitlab-ci.yml", "patch": "x"}]))
    _neg("proof tampering", make_request(
        files=[{"path": "proof/github-write/x/run.json", "patch": "x"}]))
    _neg("registry tampering completed", make_request(
        files=[{"path": "requests/completed/write/x.json", "patch": "x"}]))
    _neg("registry tampering failed", make_request(
        files=[{"path": "requests/failed/write/x.json", "patch": "x"}]))
    _neg("request tampering", make_request(
        files=[{"path": "requests/write/other.json", "patch": "x"}]))
    _neg("gate script: validator", make_request(
        files=[{"path": "scripts/validate_write_request.py", "patch": "x"}]))
    _neg("gate script: apply", make_request(
        files=[{"path": "scripts/apply_write_patch.py", "patch": "x"}]))
    _neg("gate script: proof gen", make_request(
        files=[{"path": "scripts/generate_write_proof.py", "patch": "x"}]))
    _neg("gate script: check_status", make_request(
        files=[{"path": "scripts/check_status.py", "patch": "x"}]))
    _neg("gate test file", make_request(
        files=[{"path": "scripts/test_write_validation.py", "patch": "x"}]))
    _neg("oversized single patch", make_request(
        files=[{"path": "docs/big.md", "patch": "x" * 10_001}]))
    _neg("oversized total", make_request(files=[
        {"path": f"docs/big{i}.md", "patch": "x" * 9_000}
        for i in range(6)]))
    _neg("too many files", make_request(
        files=[{"path": f"docs/f{i}.md", "patch": "x"} for i in range(11)]))
    _neg("duplicate paths", make_request(files=[
        {"path": "docs/a.md", "patch": "1"},
        {"path": "./docs/a.md", "patch": "2"}]))
    _neg("NUL byte in patch", make_request(
        files=[{"path": "docs/a.md", "patch": "x\x00y"}]))
    _neg("delete with content", make_request(
        operation="delete", files=[{"path": "docs/a.md", "patch": "x"}]))
    _neg("commit without prefix", make_request(
        commit_message="bad commit message"))
    _neg("commit wrong prefix", make_request(
        commit_message="[qwen3.8-max] spoofed"))
    _neg("commit prefix only, no subject", make_request(
        commit_message="[GLM-5.2]  "))
    _neg("unauthorized model", make_request(author_model="evil-model"))
    _neg("unknown operation", make_request(operation="rm-rf"))
    _neg("operation missing", make_request(operation=None))
    _neg("empty files", make_request(files=[]))
    _neg("files not a list", make_request(files={"path": "x"}))
    _neg("target_branch main", make_request(target_branch="main"))
    _neg("target_branch master", make_request(target_branch="master"))
    _neg("target_branch traversal", make_request(target_branch="a/../b"))
    _neg("unknown required check", make_request(
        required_checks=["deploy-to-prod"]))
    _neg("required_checks not list", make_request(
        required_checks="python-tests"))
    _neg("non-dict request", validate([1, 2, 3])[0] is False or "")


def test_validator_positives():
    valid, errors, norm = validate(VALID_BASE)
    ok = check("validator accepts canonical valid request", valid, str(errors))
    if not ok:
        return
    check("branch derived automation/glm-5.2/test-001",
          norm["target_branch"] == "automation/glm-5.2/test-001")
    check("model prefix derived", norm["model_prefix"] == "[GLM-5.2]")
    for model, prefix in (("GPT 5.6", "[GPT-5.6]"),
                          ("qwen3.8-max", "[qwen3.8-max]"),
                          ("GLM 5.2", "[GLM-5.2]")):
        v, e, n = validate(make_request(
            author_model=model, commit_message=f"{prefix} ok subject"))
        check(f"model {model} accepted with its prefix", v, str(e[:1]))
    v, _, _ = validate(make_request(target_branch=None))
    check("target_branch optional", v)
    v, _, n = validate(make_request(operation="create",
                                    files=[{"path": "docs/new.md",
                                            "patch": "# new\n"}]))
    check("create operation accepted", v)
    v, _, _ = validate(make_request(operation="delete",
                                    files=[{"path": "docs/test.md",
                                            "patch": ""}]))
    check("delete operation accepted", v)
    v, _, n = validate(make_request(commit_message="[GLM-5.2] multi\nline\r\nmsg"))
    check("commit message normalized to one line",
          v and "\n" not in n["commit_message"] and "\r" not in n["commit_message"])


def test_validator_malformed_main():
    with tempfile.TemporaryDirectory() as td:
        bad = Path(td) / "bad.json"
        bad.write_text("{ not json !", encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(HERE / "validate_write_request.py"), str(bad)],
            capture_output=True, text=True)
        ok = proc.returncode == 3 and '"malformed": true' in proc.stdout
        check("malformed JSON -> exit 3 + malformed flag", ok, proc.stdout[:120])
        missing = Path(td) / "nope.json"
        proc = subprocess.run(
            [sys.executable, str(HERE / "validate_write_request.py"),
             str(missing)], capture_output=True, text=True)
        check("missing file -> exit 3", proc.returncode == 3)


# ---------------------------------------------------------------------------
# 2. apply_write_patch — semantics & escapes
# ---------------------------------------------------------------------------

def _apply(tmp, normalized):
    from apply_write_patch import apply_request
    return apply_request(tmp, normalized)


def test_apply_operations():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "docs").mkdir()
        (root / "docs" / "existing.md").write_text("old\n", encoding="utf-8")

        r = _apply(td, {"operation": "patch", "files": [
            {"path": "docs/existing.md", "patch": "new\n"}]})
        check("patch existing ok", r["ok"] and r["count"] == 1
              and (root / "docs/existing.md").read_text() == "new\n", str(r))

        r = _apply(td, {"operation": "patch", "files": [
            {"path": "docs/missing.md", "patch": "x\n"}]})
        check("patch missing file REJECTED",
              not r["ok"] and any("requires an existing" in e for e in r["errors"]))

        r = _apply(td, {"operation": "create", "files": [
            {"path": "docs/new.md", "patch": "created\n"}]})
        check("create new ok", r["ok"]
              and (root / "docs/new.md").read_text() == "created\n")

        r = _apply(td, {"operation": "create", "files": [
            {"path": "docs/existing.md", "patch": "clobber\n"}]})
        check("create over existing REJECTED",
              not r["ok"] and (root / "docs/existing.md").read_text() == "new\n")

        r = _apply(td, {"operation": "delete", "files": [
            {"path": "docs/new.md", "patch": ""}]})
        check("delete existing ok", r["ok"]
              and not (root / "docs/new.md").exists())

        r = _apply(td, {"operation": "delete", "files": [
            {"path": "docs/gone.md", "patch": ""}]})
        check("delete missing REJECTED", not r["ok"])


def test_apply_escapes():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "docs").mkdir()
        outside = Path(td + "_outside")
        outside.mkdir(exist_ok=True)
        (outside / "victim.txt").write_text("do not touch\n", encoding="utf-8")

        r = _apply(td, {"operation": "create",
                        "files": [{"path": "..", "patch": "x"}]})
        check("bare '..' REJECTED by applier", not r["ok"])
        check("no write outside repo via '..'",
              (outside / "victim.txt").read_text() == "do not touch\n")

        # symlink directory pointing outside
        os.symlink(str(outside), str(root / "docs" / "link"))
        r = _apply(td, {"operation": "create", "files": [
            {"path": "docs/link/evil.txt", "patch": "x"}]})
        check("symlink parent escape REJECTED", not r["ok"])
        check("no write through symlinked parent",
              not (outside / "evil.txt").exists())

        # symlink file escape
        (root / "docs" / "sneak.md").symlink_to(outside / "victim.txt")
        r = _apply(td, {"operation": "patch", "files": [
            {"path": "docs/sneak.md", "patch": "pwned\n"}]})
        check("symlink file escape REJECTED", not r["ok"])
        check("symlink target untouched",
              (outside / "victim.txt").read_text() == "do not touch\n")
        shutil.rmtree(outside, ignore_errors=True)


# ---------------------------------------------------------------------------
# 3. generate_write_proof — status matrix
# ---------------------------------------------------------------------------

def _proof(env_overrides, validation=None, apply_result=None, test_result=None):
    from generate_write_proof import build_proof
    old = {}
    for k, v in env_overrides.items():
        old[k] = os.environ.get(k)
        os.environ[k] = v
    try:
        return build_proof(validation, apply_result, test_result)
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


FULL_GOOD = {
    "REQUEST_ID": "write-x", "AUTHOR_MODEL": "GLM 5.2",
    "STAGE": "pushed", "BASE_SHA": "a" * 40, "ACTUAL_BASE_SHA": "a" * 40,
    "RESULT_SHA": "b" * 40, "TARGET_BRANCH": "automation/glm-5.2/write-x",
    "PUSH_CONFIRMED": "true", "SOURCE": "gitlab", "OPERATION": "create",
}


def test_proof_matrix():
    vreq = {"valid": True, "normalized": dict(VALID_BASE, files=[
        {"path": "docs/test.md", "patch": "x"}])}
    apl = {"ok": True, "count": 1, "applied_paths": ["docs/test.md"]}
    tst = {"expected": 2, "executed": 2, "passed": 2, "failed": 0,
           "checks_executed": ["python-tests"]}

    p = _proof(FULL_GOOD, vreq, apl, tst)
    check("proof PASS on full success", p["status"] == "PASS"
          and p["stage"] == "pushed", p["status"])

    e = dict(FULL_GOOD, PUSH_CONFIRMED="false", STAGE="committed")
    p = _proof(e, vreq, apl, tst)
    check("no push -> not PASS", p["status"] == "FAIL"
          and p["stage"] == "committed")

    e = dict(FULL_GOOD, BASE_SHA="a" * 40, ACTUAL_BASE_SHA="c" * 40)
    p = _proof(e, vreq, apl, tst)
    check("base mismatch -> not PASS", p["status"] == "FAIL")

    e = dict(FULL_GOOD, STAGE="validation")
    p = _proof(e, {"valid": False, "errors": ["x"]}, None, None)
    check("validation rejection -> REJECTED", p["status"] == "REJECTED")

    e = dict(FULL_GOOD, STAGE="validation", FAIL_REASON="anti_replay")
    p = _proof(e, vreq, None, None)
    check("anti-replay -> REJECTED with reason",
          p["status"] == "REJECTED" and p["fail_reason"] == "anti_replay")

    e = dict(FULL_GOOD, STAGE="tested")
    p = _proof(e, vreq, apl, tst)
    check("stopped at tests -> FAIL", p["status"] == "FAIL")

    e = dict(FULL_GOOD, STAGE="tests")  # non-canonical stage name
    p = _proof(e, vreq, apl, tst)
    check("non-canonical stage -> UNKNOWN (fail-closed)",
          p["status"] == "UNKNOWN")

    e = dict(FULL_GOOD)
    p = _proof(e, vreq, apl, dict(tst, failed=1))
    check("failed test -> not PASS", p["status"] == "FAIL")

    p = _proof(e, vreq, apl, dict(tst, executed=1))
    check("executed != expected -> not PASS", p["status"] == "FAIL")

    p = _proof(e, vreq, apl, dict(tst, expected=0))
    check("expected == 0 -> not PASS", p["status"] == "FAIL")

    p = _proof(e, vreq, apl, dict(tst, checks_executed=[]))
    check("required check missing -> not PASS", p["status"] == "FAIL")

    p = _proof(e, vreq, {"ok": True, "count": 0, "applied_paths": []}, tst)
    check("applied != requested -> not PASS", p["status"] == "FAIL")

    p = _proof({"REQUEST_ID": "z", "STAGE": "weird"}, None, None, None)
    check("unknown stage -> UNKNOWN (fail-closed)", p["status"] == "UNKNOWN")

    p = _proof(FULL_GOOD, vreq, apl, tst)
    check("proof carries gitlab provenance",
          p["source"] == "gitlab"
          and p["source_repo"] == "gitlab.com/cheurteen/metroid")


# ---------------------------------------------------------------------------
# 4. check_status.py write profile — subprocess fail-closed
# ---------------------------------------------------------------------------

def _check_status(tmp: Path, proof: dict) -> int:
    rid = proof.get("request_id", "x")
    d = tmp / f"proof/github-write/{rid}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "run.json").write_text(json.dumps(proof), encoding="utf-8")
    env = dict(os.environ, REQUEST_ID=f"github-write/{rid}")
    proc = subprocess.run([sys.executable, str(HERE / "check_status.py")],
                          cwd=str(tmp), env=env, capture_output=True, text=True)
    return proc.returncode


def test_check_status_write_profile():
    good = {
        "schema": "github-write-proof/v1", "profile": "write",
        "request_id": "cs-ok", "author_model": "GLM 5.2",
        "base_sha": "a" * 40, "actual_base_sha": "a" * 40,
        "result_sha": "b" * 40, "branch": "automation/glm-5.2/cs-ok",
        "files_requested": 1, "files_changed": ["docs/test.md"],
        "required_checks": ["python-tests"],
        "checks_executed": ["python-tests"],
        "tests": {"expected": 2, "executed": 2, "passed": 2, "failed": 0},
        "push_confirmed": True, "stage": "pushed", "status": "PASS",
        "fail_reason": "",
    }
    with tempfile.TemporaryDirectory() as td:
        check("check_status accepts full PASS proof",
              _check_status(Path(td), good) == 0)

        bad = dict(good, request_id="cs-1", push_confirmed=False)
        check("check_status rejects push_confirmed=false",
              _check_status(Path(td), bad) != 0)

        bad = dict(good, request_id="cs-2", stage="tested")
        check("check_status rejects stage!=pushed",
              _check_status(Path(td), bad) != 0)

        bad = dict(good, request_id="cs-3",
                   tests={"expected": 0, "executed": 0, "passed": 0,
                          "failed": 0})
        check("check_status rejects tests_expected=0",
              _check_status(Path(td), bad) != 0)

        bad = dict(good, request_id="cs-4",
                   tests={"expected": 3, "executed": 2, "passed": 2,
                          "failed": 0})
        check("check_status rejects executed!=expected",
              _check_status(Path(td), bad) != 0)

        bad = dict(good, request_id="cs-5", checks_executed=[])
        check("check_status rejects missing required check",
              _check_status(Path(td), bad) != 0)

        bad = dict(good, request_id="cs-6",
                   base_sha="a" * 40, actual_base_sha="c" * 40)
        check("check_status rejects base mismatch",
              _check_status(Path(td), bad) != 0)

        bad = dict(good, request_id="cs-7", files_changed=[])
        check("check_status rejects files_changed!=files_requested",
              _check_status(Path(td), bad) != 0)


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------

def main():
    test_validator_negatives()
    test_validator_positives()
    test_validator_malformed_main()
    test_apply_operations()
    test_apply_escapes()
    test_proof_matrix()
    test_check_status_write_profile()

    passed = sum(1 for _, ok in RESULTS if ok)
    total = len(RESULTS)
    print(f"\n{'=' * 60}")
    print(f"Write relay test suite: {passed}/{total} passed")
    if passed < total:
        for name, ok in RESULTS:
            if not ok:
                print(f"  FAILED: {name}")
        sys.exit(1)
    print("All tests passed — every rejection path implies NO PUSH.")


def test_all():
    """pytest entry point."""
    main()


if __name__ == "__main__":
    main()
