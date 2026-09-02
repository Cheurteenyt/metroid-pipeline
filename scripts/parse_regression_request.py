#!/usr/bin/env python3
"""
Parse regression request JSON file.

Reads a regression request file and validates all required fields.
Outputs environment variables for use in GitHub Actions.

Exit codes:
  0 = Success
  1 = Validation error
"""

import json
import sys
import re
from pathlib import Path

def parse_and_validate(request_file: str):
    """Parse and strictly validate a regression request file."""
    
    path = Path(request_file)
    
    if not path.exists():
        print(f"ERROR: Request file not found: {request_file}", file=sys.stderr)
        sys.exit(1)
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {request_file}: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Cannot read {request_file}: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Validate required fields
    required = ['request_id', 'baseline_sha', 'candidate_sha']
    for field in required:
        if field not in data:
            print(f"ERROR: Missing required field: {field}", file=sys.stderr)
            sys.exit(1)
    
    request_id = data['request_id']
    baseline_sha = data['baseline_sha']
    candidate_sha = data['candidate_sha']
    
    # Validate SHA format (40 hex chars)
    sha_pattern = re.compile(r'^[0-9a-f]{40}$')
    
    if not sha_pattern.match(baseline_sha):
        print(f"ERROR: Invalid baseline_sha format (must be 40 hex chars): {baseline_sha}", file=sys.stderr)
        sys.exit(1)
    
    if not sha_pattern.match(candidate_sha):
        print(f"ERROR: Invalid candidate_sha format (must be 40 hex chars): {candidate_sha}", file=sys.stderr)
        sys.exit(1)
    
    # Validate baseline != candidate
    if baseline_sha == candidate_sha:
        print(f"ERROR: baseline_sha equals candidate_sha (self-comparison not allowed)", file=sys.stderr)
        sys.exit(1)
    
    # Output environment variables (for GitHub Actions)
    print(f"REQUEST_ID={request_id}")
    print(f"BASELINE_SHA={baseline_sha}")
    print(f"CANDIDATE_SHA={candidate_sha}")
    print(f"PROFILE=regression")

def main():
    if len(sys.argv) < 2:
        print("Usage: parse_regression_request.py <request_file>", file=sys.stderr)
        sys.exit(1)
    
    request_file = sys.argv[1]
    parse_and_validate(request_file)

if __name__ == '__main__':
    main()
