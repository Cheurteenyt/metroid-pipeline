#!/usr/bin/env python3
"""Apply a validated write request patch to the working tree.

This script ONLY applies patches that passed validate_write_request.py.
It does NOT push — that's the workflow's job after tests pass.
"""
import json
import os
import sys
from pathlib import Path

def apply_patch(repo_root: str, files: list) -> list:
    """Apply file patches. Returns list of (path, action) tuples."""
    changes = []
    root = Path(repo_root)
    
    for f in files:
        path = f["path"]
        content = f.get("patch", "")
        full_path = root / path
        
        # Ensure parent dir exists
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the file
        full_path.write_text(content, encoding="utf-8")
        changes.append((path, "patched"))
    
    return changes


def main():
    if len(sys.argv) < 3:
        print("Usage: apply_write_patch.py <repo_root> <normalized_request.json>")
        sys.exit(1)
    
    repo_root = sys.argv[1]
    request_path = sys.argv[2]
    
    with open(request_path) as f:
        request = json.load(f)
    
    changes = apply_patch(repo_root, request.get("files", []))
    
    print(f"Applied {len(changes)} file changes:")
    for path, action in changes:
        print(f"  {action}: {path}")


if __name__ == "__main__":
    main()
