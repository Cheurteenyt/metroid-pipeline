#!/usr/bin/env python3
"""
Regression comparison for verified manifests.

Compares baseline and candidate verified_manifest.json files to detect:
- Functions lost (in baseline but not in candidate)
- Fingerprint changes (same function, different fingerprint)
- Count decreases

Exit codes:
  0 = no regressions
  2 = regressions detected
"""

import argparse
import json
import sys
from pathlib import Path

def load_manifest(path: Path) -> dict:
    """Load and validate a verified manifest."""
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception as e:
        print(f"ERROR: Cannot read {path}: {e}", file=sys.stderr)
        sys.exit(2)
    
    if 'verified' not in data:
        print(f"ERROR: {path} missing 'verified' key", file=sys.stderr)
        sys.exit(2)
    
    return data

def compare_manifests(baseline: dict, candidate: dict) -> tuple[bool, list[str]]:
    """
    Compare two manifests and return (passed, errors).
    
    Rules:
    1. Every function in baseline must exist in candidate
    2. Fingerprint must be unchanged
    3. Candidate count must not decrease
    """
    errors = []
    
    b_verified = baseline.get('verified', {})
    c_verified = candidate.get('verified', {})
    
    b_count = len(b_verified)
    c_count = len(c_verified)
    
    print(f"Baseline: {b_count} EXACT functions")
    print(f"Candidate: {c_count} EXACT functions")
    
    # Rule 1: Check for lost functions
    lost = []
    for symbol in b_verified.keys():
        if symbol not in c_verified:
            lost.append(symbol)
    
    if lost:
        errors.append(f"Lost {len(lost)} functions:")
        for symbol in lost[:10]:  # Show first 10
            errors.append(f"  - {symbol}")
        if len(lost) > 10:
            errors.append(f"  ... and {len(lost) - 10} more")
    
    # Rule 2: Check for fingerprint changes
    changed = []
    for symbol in b_verified.keys():
        if symbol in c_verified:
            b_fp = b_verified[symbol].get('fingerprint', '')
            c_fp = c_verified[symbol].get('fingerprint', '')
            if b_fp != c_fp:
                changed.append(symbol)
    
    if changed:
        errors.append(f"Fingerprint changed for {len(changed)} functions:")
        for symbol in changed[:10]:
            errors.append(f"  - {symbol}")
        if len(changed) > 10:
            errors.append(f"  ... and {len(changed) - 10} more")
    
    # Rule 3: Count must not decrease
    if c_count < b_count:
        errors.append(f"Count decreased: {b_count} -> {c_count} ({c_count - b_count} lost)")
    
    passed = len(errors) == 0
    return passed, errors

def main():
    parser = argparse.ArgumentParser(description='Compare verified manifests')
    parser.add_argument('--baseline', required=True, type=Path, help='Baseline manifest')
    parser.add_argument('--candidate', required=True, type=Path, help='Candidate manifest')
    parser.add_argument('--output', type=Path, help='Output JSON file')
    
    args = parser.parse_args()
    
    print(f"Loading baseline: {args.baseline}")
    baseline = load_manifest(args.baseline)
    
    print(f"Loading candidate: {args.candidate}")
    candidate = load_manifest(args.candidate)
    
    print("\nComparing manifests...")
    passed, errors = compare_manifests(baseline, candidate)
    
    if passed:
        print("\n✅ PASS: No regressions detected")
        result = {'status': 'PASS', 'errors': []}
    else:
        print("\n❌ FAIL: Regressions detected")
        for error in errors:
            print(error)
        result = {'status': 'FAIL', 'errors': errors}
    
    if args.output:
        args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(f"\nResults written to {args.output}")
    
    sys.exit(0 if passed else 2)

if __name__ == '__main__':
    main()
