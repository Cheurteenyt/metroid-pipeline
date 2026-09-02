#!/usr/bin/env python3
"""Negative tests for regression workflow (v2 - real SHA-256 fingerprints).

Test cases:
  A: PASS - identical manifests (real SHA-256 fingerprints)
  B: FAIL - function lost
  C: FAIL - fingerprint changed
  D: FAIL - manifest missing
  E: FAIL - invalid JSON
  F: FAIL - baseline == candidate (self-comparison)
  G: FAIL - inconsistent run.json (PASS with null counts)
  H: FAIL - invalid fingerprint format (sha256:111 rejected)
  I: Lifecycle test - synthetic FAIL proof -> request NOT in completed/
  J: PASS - complete valid proof with comparison.json
"""

import json
import sys
import subprocess
import tempfile
import os
from pathlib import Path

# Real SHA-256 fingerprints for testing (64 hex chars)
SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64

def create_test_manifests(tmpdir: Path, baseline_data: dict, candidate_data: dict):
    """Create baseline and candidate manifest files."""
    baseline_path = tmpdir / "baseline.json"
    candidate_path = tmpdir / "candidate.json"
    
    with open(baseline_path, 'w') as f:
        json.dump(baseline_data, f, indent=2)
    
    with open(candidate_path, 'w') as f:
        json.dump(candidate_data, f, indent=2)
    
    return baseline_path, candidate_path

def test_a_pass_identical():
    """Test A: PASS with identical manifests (real SHA-256)."""
    print("\n=== Test A: PASS - identical manifests ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        manifest = {
            "verified": {
                "func_A": {"fingerprint": SHA_A, "class": "A", "kind": "get"},
                "func_B": {"fingerprint": SHA_B, "class": "B", "kind": "set"}
            }
        }
        
        baseline_path, candidate_path = create_test_manifests(tmpdir, manifest, manifest)
        
        result = subprocess.run(
            ["python3", "scripts/regression_compare.py",
             "--baseline", str(baseline_path),
             "--candidate", str(candidate_path),
             "--output", str(tmpdir / "comparison.json")],
            capture_output=True,
            text=True
        )
        
        print(f"Exit code: {result.returncode}")
        
        if result.returncode == 0:
            print("✅ Test A PASSED")
            return True
        else:
            print(f"❌ Test A FAILED: {result.stderr[:200]}")
            return False

def test_b_fail_function_lost():
    """Test B: FAIL when function is lost."""
    print("\n=== Test B: FAIL - function lost ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        baseline = {
            "verified": {
                "func_A": {"fingerprint": SHA_A, "class": "A", "kind": "get"},
                "func_B": {"fingerprint": SHA_B, "class": "B", "kind": "set"}
            }
        }
        
        candidate = {
            "verified": {
                "func_A": {"fingerprint": SHA_A, "class": "A", "kind": "get"}
            }
        }
        
        baseline_path, candidate_path = create_test_manifests(tmpdir, baseline, candidate)
        
        result = subprocess.run(
            ["python3", "scripts/regression_compare.py",
             "--baseline", str(baseline_path),
             "--candidate", str(candidate_path),
             "--output", str(tmpdir / "comparison.json")],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 2:
            print("✅ Test B PASSED")
            return True
        else:
            print(f"❌ Test B FAILED: exit code {result.returncode}")
            return False

def test_c_fail_fingerprint_changed():
    """Test C: FAIL when fingerprint changed."""
    print("\n=== Test C: FAIL - fingerprint changed ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        baseline = {
            "verified": {
                "func_A": {"fingerprint": SHA_A, "class": "A", "kind": "get"}
            }
        }
        
        candidate = {
            "verified": {
                "func_A": {"fingerprint": SHA_C, "class": "A", "kind": "get"}
            }
        }
        
        baseline_path, candidate_path = create_test_manifests(tmpdir, baseline, candidate)
        
        result = subprocess.run(
            ["python3", "scripts/regression_compare.py",
             "--baseline", str(baseline_path),
             "--candidate", str(candidate_path),
             "--output", str(tmpdir / "comparison.json")],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 2:
            print("✅ Test C PASSED")
            return True
        else:
            print(f"❌ Test C FAILED: exit code {result.returncode}")
            return False

def test_d_fail_manifest_missing():
    """Test D: FAIL when manifest is missing."""
    print("\n=== Test D: FAIL - manifest missing ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        baseline = {
            "verified": {
                "func_A": {"fingerprint": SHA_A, "class": "A", "kind": "get"}
            }
        }
        
        baseline_path = tmpdir / "baseline.json"
        with open(baseline_path, 'w') as f:
            json.dump(baseline, f)
        
        candidate_path = tmpdir / "candidate.json"
        
        result = subprocess.run(
            ["python3", "scripts/regression_compare.py",
             "--baseline", str(baseline_path),
             "--candidate", str(candidate_path),
             "--output", str(tmpdir / "comparison.json")],
            capture_output=True,
            text=True
        )
        
        if result.returncode in [2, 3]:
            print("✅ Test D PASSED")
            return True
        else:
            print(f"❌ Test D FAILED: exit code {result.returncode}")
            return False

def test_e_fail_invalid_json():
    """Test E: FAIL when JSON is invalid."""
    print("\n=== Test E: FAIL - invalid JSON ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        baseline = {
            "verified": {
                "func_A": {"fingerprint": SHA_A, "class": "A", "kind": "get"}
            }
        }
        
        baseline_path = tmpdir / "baseline.json"
        with open(baseline_path, 'w') as f:
            json.dump(baseline, f)
        
        candidate_path = tmpdir / "candidate.json"
        with open(candidate_path, 'w') as f:
            f.write("{ invalid json }")
        
        result = subprocess.run(
            ["python3", "scripts/regression_compare.py",
             "--baseline", str(baseline_path),
             "--candidate", str(candidate_path),
             "--output", str(tmpdir / "comparison.json")],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 3:
            print("✅ Test E PASSED")
            return True
        else:
            print(f"❌ Test E FAILED: exit code {result.returncode}")
            return False

def test_f_fail_baseline_equals_candidate():
    """Test F: FAIL when baseline == candidate."""
    print("\n=== Test F: FAIL - baseline equals candidate ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        request_file = tmpdir / "request.json"
        request_data = {
            "request_id": "test-0001",
            "baseline_sha": "a" * 40,
            "candidate_sha": "a" * 40
        }
        
        with open(request_file, 'w') as f:
            json.dump(request_data, f)
        
        result = subprocess.run(
            ["python3", "scripts/parse_regression_request.py", str(request_file)],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 1:
            print("✅ Test F PASSED")
            return True
        else:
            print(f"❌ Test F FAILED: exit code {result.returncode}")
            return False

def test_g_fail_inconsistent_run_json():
    """Test G: FAIL when run.json has inconsistent fields."""
    print("\n=== Test G: FAIL - inconsistent run.json ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        run_json = {
            "request_id": "test-0001",
            "profile": "regression",
            "status": "PASS",
            "baseline_sha": "a" * 40,
            "candidate_sha": "b" * 40,
            "baseline_actual": "a" * 40,
            "candidate_actual": "b" * 40,
            "baseline_exact_count": None,
            "candidate_exact_count": None,
            "lost_count": 0,
            "changed_count": 0,
            "timestamp_utc": "2026-01-01T00:00:00Z"
        }
        
        proof_dir = tmpdir / "proof" / "test-0001"
        proof_dir.mkdir(parents=True)
        
        run_json_path = proof_dir / "run.json"
        with open(run_json_path, 'w') as f:
            json.dump(run_json, f)
        
        env = os.environ.copy()
        env["REQUEST_ID"] = "test-0001"
        env["GITHUB_WORKSPACE"] = str(tmpdir)
        
        result = subprocess.run(
            ["python3", "scripts/check_status.py"],
            capture_output=True,
            text=True,
            cwd=tmpdir,
            env=env
        )
        
        if result.returncode == 1:
            print("✅ Test G PASSED")
            return True
        else:
            print(f"❌ Test G FAILED: exit code {result.returncode}")
            return False

def test_h_fail_invalid_fingerprint():
    """Test H: FAIL when fingerprint is not valid SHA-256."""
    print("\n=== Test H: FAIL - invalid fingerprint format ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        baseline = {
            "verified": {
                "func_A": {"fingerprint": "sha256:111", "class": "A", "kind": "get"}
            }
        }
        
        baseline_path, candidate_path = create_test_manifests(tmpdir, baseline, baseline)
        
        result = subprocess.run(
            ["python3", "scripts/regression_compare.py",
             "--baseline", str(baseline_path),
             "--candidate", str(candidate_path),
             "--output", str(tmpdir / "comparison.json")],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 3:
            print("✅ Test H PASSED: invalid fingerprint rejected")
            return True
        else:
            print(f"❌ Test H FAILED: exit code {result.returncode}")
            return False

def test_i_lifecycle_fail():
    """Test I: Lifecycle - synthetic FAIL proof -> request NOT in completed/."""
    print("\n=== Test I: Lifecycle - FAIL proof not in completed ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        run_json = {
            "request_id": "test-fail",
            "profile": "regression",
            "status": "FAIL",
            "reason": "functions_lost:5",
            "baseline_sha": "a" * 40,
            "candidate_sha": "b" * 40,
            "baseline_actual": "a" * 40,
            "candidate_actual": "b" * 40,
            "baseline_exact_count": 10,
            "candidate_exact_count": 5,
            "lost_count": 5,
            "changed_count": 0,
            "timestamp_utc": "2026-01-01T00:00:00Z"
        }
        
        proof_dir = tmpdir / "proof" / "test-fail"
        proof_dir.mkdir(parents=True)
        
        with open(proof_dir / "run.json", 'w') as f:
            json.dump(run_json, f)
        
        env = os.environ.copy()
        env["REQUEST_ID"] = "test-fail"
        env["GITHUB_WORKSPACE"] = str(tmpdir)
        
        result = subprocess.run(
            ["python3", "scripts/check_status.py"],
            capture_output=True,
            text=True,
            cwd=tmpdir,
            env=env
        )
        
        if result.returncode != 0:
            print("✅ Test I PASSED: check_status.py exited non-zero for FAIL")
            return True
        else:
            print(f"❌ Test I FAILED: check_status.py should exit non-zero for FAIL")
            return False

def test_j_pass_complete_proof():
    """Test J: PASS with complete valid proof + comparison.json."""
    print("\n=== Test J: PASS - complete valid proof ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        run_json = {
            "request_id": "test-pass",
            "profile": "regression",
            "status": "PASS",
            "reason": "no_regressions",
            "baseline_sha": "a" * 40,
            "candidate_sha": "b" * 40,
            "baseline_actual": "a" * 40,
            "candidate_actual": "b" * 40,
            "baseline_exact_count": 10,
            "candidate_exact_count": 12,
            "lost_count": 0,
            "changed_count": 0,
            "timestamp_utc": "2026-01-01T00:00:00Z"
        }
        
        comparison = {
            "status": "PASS",
            "reason": "no_regressions",
            "baseline_count": 10,
            "candidate_count": 12,
            "lost_count": 0,
            "changed_count": 0
        }
        
        proof_dir = tmpdir / "proof" / "test-pass"
        proof_dir.mkdir(parents=True)
        
        with open(proof_dir / "run.json", 'w') as f:
            json.dump(run_json, f)
        
        with open(proof_dir / "comparison.json", 'w') as f:
            json.dump(comparison, f)
        
        env = os.environ.copy()
        env["REQUEST_ID"] = "test-pass"
        env["GITHUB_WORKSPACE"] = str(tmpdir)
        
        result = subprocess.run(
            ["python3", "scripts/check_status.py"],
            capture_output=True,
            text=True,
            cwd=tmpdir,
            env=env
        )
        
        if result.returncode == 0:
            print("✅ Test J PASSED")
            return True
        else:
            print(f"❌ Test J FAILED: exit code {result.returncode}")
            print(f"stdout: {result.stdout}")
            print(f"stderr: {result.stderr}")
            return False

def main():
    print("=" * 70)
    print("REGRESSION WORKFLOW NEGATIVE TESTS (v2)")
    print("=" * 70)
    
    tests = [
        test_a_pass_identical,
        test_b_fail_function_lost,
        test_c_fail_fingerprint_changed,
        test_d_fail_manifest_missing,
        test_e_fail_invalid_json,
        test_f_fail_baseline_equals_candidate,
        test_g_fail_inconsistent_run_json,
        test_h_fail_invalid_fingerprint,
        test_i_lifecycle_fail,
        test_j_pass_complete_proof
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        sys.exit(1)

if __name__ == '__main__':
    main()
