#!/usr/bin/env python3
"""Negative tests for github-write-request/v1 validation.

Every test case must produce INVALID (no push possible).
"""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from validate_write_request import validate

VALID_BASE = {
    "schema": "github-write-request/v1",
    "request_id": "test-001",
    "target_repo": "Cheurteenyt/metroid-pipeline",
    "target_branch": "test/branch",
    "base_sha": "a" * 40,
    "author_model": "GLM 5.2",
    "operation": "patch",
    "files": [{"path": "docs/test.md", "patch": "# test"}],
    "commit_message": "[GLM-5.2] test commit",
    "required_checks": ["python-tests"],
}


def make_request(**overrides):
    req = dict(VALID_BASE)
    for k, v in overrides.items():
        if v is None:
            req.pop(k, None)
        else:
            req[k] = v
    return req


def expect_invalid(name, request):
    valid, errors, _ = validate(request)
    if valid:
        print(f"FAIL: {name} — should be INVALID but was VALID")
        return False
    print(f"PASS: {name} — correctly rejected ({errors[0][:50]})")
    return True


def main():
    results = []
    
    # A: bad schema
    results.append(expect_invalid("A: bad schema",
        make_request(schema="wrong")))
    
    # B: empty request_id
    results.append(expect_invalid("B: empty request_id",
        make_request(request_id="")))
    
    # C: wrong repo
    results.append(expect_invalid("C: wrong repo",
        make_request(target_repo="evil/repo")))
    
    # D: SHA too short
    results.append(expect_invalid("D: SHA 39 chars",
        make_request(base_sha="a" * 39)))
    
    # E: SHA non-hex
    results.append(expect_invalid("E: SHA non-hex",
        make_request(base_sha="g" * 40)))
    
    # F: path traversal
    results.append(expect_invalid("F: path traversal",
        make_request(files=[{"path": "../evil.py", "patch": "x"}])))
    
    # G: absolute path
    results.append(expect_invalid("G: absolute path",
        make_request(files=[{"path": "/etc/passwd", "patch": "x"}])))
    
    # H: workflow modification
    results.append(expect_invalid("H: workflow mod",
        make_request(files=[{"path": ".github/workflows/evil.yml", "patch": "x"}])))
    
    # I: secret file
    results.append(expect_invalid("I: secret file",
        make_request(files=[{"path": "secrets/token.key", "patch": "x"}])))
    
    # J: .env file
    results.append(expect_invalid("J: .env file",
        make_request(files=[{"path": ".env", "patch": "x"}])))
    
    # K: .pem file
    results.append(expect_invalid("K: .pem file",
        make_request(files=[{"path": "cert.pem", "patch": "x"}])))
    
    # L: patch too large
    big_patch = "x" * 10001
    results.append(expect_invalid("L: patch too large",
        make_request(files=[{"path": "docs/big.md", "patch": big_patch}])))
    
    # M: too many files
    many_files = [{"path": f"docs/f{i}.md", "patch": "x"} for i in range(11)]
    results.append(expect_invalid("M: too many files",
        make_request(files=many_files)))
    
    # N: commit message without prefix
    results.append(expect_invalid("N: no prefix",
        make_request(commit_message="bad commit message")))
    
    # O: unauthorized model
    results.append(expect_invalid("O: unauthorized model",
        make_request(author_model="evil-model")))
    
    # P: unknown operation
    results.append(expect_invalid("P: unknown operation",
        make_request(operation="rm-rf")))
    
    # Q: empty files
    results.append(expect_invalid("Q: empty files",
        make_request(files=[])))
    
    # R: main branch target
    results.append(expect_invalid("R: main branch",
        make_request(target_branch="main")))
    
    # S: master branch target
    results.append(expect_invalid("S: master branch",
        make_request(target_branch="master")))
    
    # T: valid request should pass
    valid, errors, normalized = validate(VALID_BASE)
    if valid and normalized:
        print(f"PASS: T: valid request accepted")
        results.append(True)
    else:
        print(f"FAIL: T: valid request rejected: {errors}")
        results.append(False)
    
    passed = sum(results)
    total = len(results)
    print(f"\n{'='*50}")
    print(f"Write relay validation tests: {passed}/{total} passed")
    
    if passed < total:
        sys.exit(1)
    print("All tests passed!")


if __name__ == "__main__":
    main()
