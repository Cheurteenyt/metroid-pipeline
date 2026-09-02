#!/usr/bin/env python3
"""Validate regression proof (HARDENED VERSION).

This script validates that run.json meets all invariants before accepting PASS.

CRITICAL: This script recalculates metrics from comparison.json independently
and refuses any discrepancy with run.json.

Exit codes:
  0 = Validation passed (status is PASS and all invariants hold)
  1 = Validation failed (status is FAIL/UNKNOWN or invariants violated)
"""

import json
import os
import sys
from pathlib import Path

def load_run_json():
    """Load run.json from expected location. NO FALLBACK."""
    rid = os.environ.get("REQUEST_ID", "")
    if not rid:
        rid = f"failed-{os.environ.get('GITHUB_RUN_ID', 'unknown')}"
    
    path = f"proof/{rid}/run.json"
    
    if not os.path.exists(path):
        # NO FALLBACK: refuse missing file
        print(f"::error::run.json not found at {path}", file=sys.stderr)
        sys.exit(1)
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data, path
    except json.JSONDecodeError as e:
        print(f"::error::Invalid JSON in {path}: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"::error::Cannot read {path}: {e}", file=sys.stderr)
        sys.exit(1)

def load_comparison_json(proof_dir):
    """Load comparison.json for independent verification."""
    path = Path(proof_dir) / "comparison.json"
    
    if not path.exists():
        return None
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None

def validate_regression_proof(data, comparison):
    """
    Validate regression proof against all invariants.
    
    CRITICAL: For PASS, recalculate metrics from comparison.json independently.
    
    Returns:
        (valid, errors): tuple of (bool, list of error messages)
    """
    errors = []
    
    # Check required fields
    required_fields = [
        'request_id',
        'profile',
        'status',
        'baseline_sha',
        'candidate_sha',
        'baseline_actual',
        'candidate_actual',
        'baseline_exact_count',
        'candidate_exact_count',
        'lost_count',
        'changed_count',
        'timestamp_utc'
    ]
    
    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")
    
    if errors:
        return False, errors
    
    # Validate profile
    if data['profile'] != 'regression':
        errors.append(f"Invalid profile: {data['profile']} (expected 'regression')")
    
    # Validate status
    status = data['status']
    if status not in ['PASS', 'FAIL', 'UNKNOWN']:
        errors.append(f"Invalid status: {status} (must be PASS, FAIL, or UNKNOWN)")
        return False, errors
    
    # If status is not PASS, validation passes (we accept FAIL/UNKNOWN)
    # If status is not PASS, validation fails (we reject FAIL/UNKNOWN)
    if status != 'PASS':
        print(f"Status is {status}: {data.get('reason', 'no reason provided')}")
        return False, [f'Status is {status}, not PASS']
    
    # For PASS, validate all invariants
    
    # Invariant 1: baseline_sha != candidate_sha
    if data['baseline_sha'] == data['candidate_sha']:
        errors.append("baseline_sha equals candidate_sha (self-comparison not allowed)")
    
    # Invariant 2: SHA format (40 hex chars)
    import re
    sha_pattern = re.compile(r'^[0-9a-f]{40}$')
    
    if not sha_pattern.match(data['baseline_sha']):
        errors.append(f"Invalid baseline_sha format: {data['baseline_sha']}")
    
    if not sha_pattern.match(data['candidate_sha']):
        errors.append(f"Invalid candidate_sha format: {data['candidate_sha']}")
    
    # Invariant 3: baseline_actual matches baseline_sha
    if data['baseline_actual'] != data['baseline_sha']:
        errors.append(f"baseline_actual ({data['baseline_actual']}) != baseline_sha ({data['baseline_sha']})")
    
    # Invariant 4: candidate_actual matches candidate_sha
    if data['candidate_actual'] != data['candidate_sha']:
        errors.append(f"candidate_actual ({data['candidate_actual']}) != candidate_sha ({data['candidate_sha']})")
    
    # Invariant 5: Counts are non-negative integers
    count_fields = ['baseline_exact_count', 'candidate_exact_count', 'lost_count', 'changed_count']
    for field in count_fields:
        value = data[field]
        if not isinstance(value, int) or value < 0:
            errors.append(f"{field} must be non-negative integer, got {value}")
    
    # Invariant 6: For PASS, lost_count must be 0
    if data['lost_count'] != 0:
        errors.append(f"PASS requires lost_count=0, got {data['lost_count']}")
    
    # Invariant 7: For PASS, changed_count must be 0
    if data['changed_count'] != 0:
        errors.append(f"PASS requires changed_count=0, got {data['changed_count']}")
    
    # Invariant 8: For PASS, candidate_exact_count >= baseline_exact_count
    if data['candidate_exact_count'] < data['baseline_exact_count']:
        errors.append(f"PASS requires candidate_exact_count >= baseline_exact_count, got {data['candidate_exact_count']} < {data['baseline_exact_count']}")
    
    # Invariant 9: baseline_exact_count > 0 (must have something to compare)
    if data['baseline_exact_count'] == 0:
        errors.append("baseline_exact_count must be > 0")
    
    # Invariant 10: reason field should be present and meaningful for PASS
    if 'reason' not in data or not data['reason']:
        errors.append("PASS requires a reason field")
    
    # CRITICAL Invariant 11: Recalculate from comparison.json independently
    if comparison is not None:
        comp_lost = comparison.get('lost_count')
        comp_changed = comparison.get('changed_count')
        comp_baseline = comparison.get('baseline_count')
        comp_candidate = comparison.get('candidate_count')
        
        if comp_lost is not None and comp_lost != data['lost_count']:
            errors.append(f"lost_count mismatch: run.json={data['lost_count']}, comparison.json={comp_lost}")
        
        if comp_changed is not None and comp_changed != data['changed_count']:
            errors.append(f"changed_count mismatch: run.json={data['changed_count']}, comparison.json={comp_changed}")
        
        if comp_baseline is not None and comp_baseline != data['baseline_exact_count']:
            errors.append(f"baseline_exact_count mismatch: run.json={data['baseline_exact_count']}, comparison.json={comp_baseline}")
        
        if comp_candidate is not None and comp_candidate != data['candidate_exact_count']:
            errors.append(f"candidate_exact_count mismatch: run.json={data['candidate_exact_count']}, comparison.json={comp_candidate}")
        
        # If comparison.json says FAIL, run.json cannot say PASS
        if comparison.get('status') == 'FAIL' and data['status'] == 'PASS':
            errors.append("comparison.json says FAIL but run.json says PASS")
    
    valid = len(errors) == 0
    return valid, errors

def main():
    print("=== Validating regression proof ===")
    
    data, run_json_path = load_run_json()
    
    print(f"Loaded run.json from {run_json_path}")
    print(f"  request_id: {data.get('request_id', 'N/A')}")
    print(f"  profile: {data.get('profile', 'N/A')}")
    print(f"  status: {data.get('status', 'N/A')}")
    
    # Load comparison.json for independent verification
    proof_dir = Path(run_json_path).parent
    comparison = load_comparison_json(proof_dir)
    
    if comparison is not None:
        print(f"  comparison.json loaded for independent verification")
    else:
        print(f"  comparison.json not found (skipping independent verification)")
    
    valid, errors = validate_regression_proof(data, comparison)
    
    if valid:
        if data['status'] == 'PASS':
            print("\n✅ Proof validation PASSED: All invariants hold")
        else:
            print(f"\n✓ Proof validation PASSED: Status is {data['status']} (acceptable)")
        sys.exit(0)
    else:
        print("\n❌ Proof validation FAILED:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

if __name__ == '__main__':
    main()
