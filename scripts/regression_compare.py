#!/usr/bin/env python3
"""Regression comparison for verified manifests (HARDENED v2).

Fixes vs v1:
  - Fingerprint must match ^sha256:[0-9a-f]{64}$ (real SHA-256), not just a prefix.
  - Privacy preserved: only aggregated counts are reported.

Exit codes:
  0 = PASS (no regressions)
  2 = FAIL (regressions detected)
  3 = UNKNOWN (validation error / malformed data)
"""
import argparse, json, re, sys
from pathlib import Path

FP_RE = re.compile(r'^sha256:[0-9a-f]{64}$')

def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(3)

def load_manifest(path):
    if not path.exists():
        fail(f"file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        fail(f"invalid JSON in {path}: {e}")
    except Exception as e:
        fail(f"cannot read {path}: {e}")
    if not isinstance(data, dict):
        fail(f"{path} is not a JSON object")
    if 'verified' not in data:
        fail(f"{path} missing 'verified' key")
    verified = data['verified']
    if not isinstance(verified, dict):
        fail(f"{path} 'verified' is not a dict")
    for sym, entry in verified.items():
        if not isinstance(entry, dict):
            fail(f"{path} entry not a dict")
        fp = entry.get('fingerprint')
        if not isinstance(fp, str):
            fail(f"{path} fingerprint not a string")
        if not FP_RE.match(fp):
            fail(f"{path} fingerprint is not a valid sha256 (64 hex): {fp[:50]}...")
    return data

def compare(baseline, candidate):
    b = baseline.get('verified', {})
    c = candidate.get('verified', {})
    lost = [s for s in b if s not in c]
    changed = [s for s in b if s in c and b[s].get('fingerprint') != c[s].get('fingerprint')]
    metrics = {
        'baseline_count': len(b),
        'candidate_count': len(c),
        'lost_count': len(lost),
        'changed_count': len(changed)
    }
    if lost:
        return 'FAIL', f'functions_lost:{len(lost)}', metrics
    if changed:
        return 'FAIL', f'fingerprints_changed:{len(changed)}', metrics
    if len(c) < len(b):
        return 'FAIL', f'count_decreased:{len(b)}->{len(c)}', metrics
    return 'PASS', 'no_regressions', metrics

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--baseline', required=True, type=Path)
    p.add_argument('--candidate', required=True, type=Path)
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    baseline = load_manifest(a.baseline)
    candidate = load_manifest(a.candidate)
    status, reason, m = compare(baseline, candidate)
    print(f"baseline={m['baseline_count']} candidate={m['candidate_count']} lost={m['lost_count']} changed={m['changed_count']}")
    print(('PASS: ' if status=='PASS' else 'FAIL: ') + reason)
    result = {'status': status, 'reason': reason, **m}
    if a.output:
        a.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    sys.exit(0 if status=='PASS' else 2)

if __name__ == '__main__':
    main()
