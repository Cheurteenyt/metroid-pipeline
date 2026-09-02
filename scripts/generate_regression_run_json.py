#!/usr/bin/env python3
"""
Generate run.json for regression profile (HARDENED VERSION).

Uses Python json.dump() for safe JSON generation.
Never uses shell interpolation to avoid malformed JSON.

Exit codes:
  0 = Success
  1 = Error
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

def get_env(key: str, default: str = "") -> str:
    """Get environment variable with default."""
    return os.environ.get(key, default)

def get_env_int(key: str, default: int = 0) -> int:
    """Get environment variable as int with default."""
    try:
        return int(os.environ.get(key, str(default)))
    except (ValueError, TypeError):
        return default

def main():
    # Get request ID
    request_id = get_env("REQUEST_ID")
    if not request_id:
        request_id = f"failed-{os.environ.get('GITHUB_RUN_ID', 'unknown')}"
    
    # Build proof directory
    proof_dir = Path(f"proof/{request_id}")
    proof_dir.mkdir(parents=True, exist_ok=True)
    
    # Build run.json with all required fields
    data = {
        # Core identification
        "request_id": request_id,
        "profile": "regression",
        "runner_repo": "Cheurteenyt/metroid-pipeline",
        "runner_commit": get_env("GITHUB_SHA"),
        "trigger_commit": get_env("GITHUB_SHA"),
        
        # Regression-specific fields
        "baseline_sha": get_env("BASELINE_SHA"),
        "candidate_sha": get_env("CANDIDATE_SHA"),
        "baseline_actual": get_env("BASELINE_ACTUAL"),
        "candidate_actual": get_env("CANDIDATE_ACTUAL"),
        
        # Status and reason
        "status": get_env("REGRESSION_STATUS", "UNKNOWN"),
        "reason": get_env("REGRESSION_REASON", "not_evaluated"),
        
        # Metrics (aggregated counts only, NO private symbols)
        "baseline_exact_count": get_env_int("BASELINE_EXACT_COUNT", 0),
        "candidate_exact_count": get_env_int("CANDIDATE_EXACT_COUNT", 0),
        "lost_count": get_env_int("LOST_COUNT", 0),
        "changed_count": get_env_int("CHANGED_COUNT", 0),
        
        # Reference pack integrity
        "reference_elf_sha256": get_env("REFERENCE_ELF_SHA256"),
        "reference_symbols_sha256": get_env("REFERENCE_SYMBOLS_SHA256"),
        
        # Timestamp
        "timestamp_utc": datetime.now(timezone.utc).isoformat()
    }
    
    # Write JSON safely
    run_json_path = proof_dir / "run.json"
    
    try:
        with open(run_json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✓ run.json written to {run_json_path}")
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: Failed to write run.json: {e}", file=sys.stderr)
        # Write minimal fallback
        fallback = {
            "request_id": request_id,
            "profile": "regression",
            "status": "UNKNOWN",
            "reason": "proof_generation_failed"
        }
        with open(run_json_path, 'w', encoding='utf-8') as f:
            json.dump(fallback, f, indent=2)
        sys.exit(1)

if __name__ == '__main__':
    main()
