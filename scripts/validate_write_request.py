#!/usr/bin/env python3
"""Validate a github-write-request/v1 payload.

Returns (valid, errors, normalized_request).
Never trusts the request — always re-derives safe values.
"""
import json
import os
import re
import sys
from pathlib import Path

SCHEMA = "github-write-request/v1"
ALLOWED_MODELS = {"GPT 5.6", "qwen3.8-max", "GLM 5.2"}
TARGET_REPO = "Cheurteenyt/metroid-pipeline"
MAX_FILES = 10
MAX_PATCH_BYTES = 50_000
MAX_FILE_BYTES = 10_000

# Paths that must NEVER be modified
DENY_PATTERNS = [
    re.compile(r'^\.github/workflows/'),
    re.compile(r'^\.git/'),
    re.compile(r'^\.gitmodules$'),
    re.compile(r'^secrets/'),
    re.compile(r'^\.env'),
    re.compile(r'\.pem$'),
    re.compile(r'\.key$'),
    re.compile(r'\.\./'),  # path traversal
    re.compile(r'^/'),     # absolute paths (original)
    re.compile(r'^[a-zA-Z]:'), # Windows absolute paths
]

def validate(request: dict) -> tuple:
    errors = []
    
    # Schema
    if request.get("schema") != SCHEMA:
        errors.append(f"Invalid schema: expected '{SCHEMA}'")
        return False, errors, None
    
    # request_id
    rid = request.get("request_id", "")
    if not rid or not isinstance(rid, str):
        errors.append("request_id must be non-empty string")
    elif not re.match(r'^[a-zA-Z0-9_-]+$', rid):
        errors.append(f"request_id contains invalid chars: {rid}")
    
    # target_repo
    if request.get("target_repo") != TARGET_REPO:
        errors.append(f"target_repo must be '{TARGET_REPO}'")
    
    # author_model
    model = request.get("author_model", "")
    if model not in ALLOWED_MODELS:
        errors.append(f"author_model must be one of {ALLOWED_MODELS}")
    
    # base_sha
    base_sha = request.get("base_sha", "")
    if not re.match(r'^[0-9a-f]{40}$', base_sha):
        errors.append(f"base_sha must be 40 hex chars, got {len(base_sha)}")
    
    # target_branch
    branch = request.get("target_branch", "")
    if not branch:
        errors.append("target_branch must be non-empty")
    elif branch in ("main", "master"):
        errors.append("target_branch must not be main/master")
    elif not re.match(r'^[a-zA-Z0-9/_.-]+$', branch):
        errors.append(f"target_branch contains invalid chars: {branch}")
    
    # operation
    op = request.get("operation", "")
    if op not in ("patch", "create", "delete"):
        errors.append(f"operation must be patch/create/delete, got '{op}'")
    
    # files
    files = request.get("files", [])
    if not isinstance(files, list):
        errors.append("files must be a list")
        files = []
    if len(files) == 0:
        errors.append("files must not be empty")
    if len(files) > MAX_FILES:
        errors.append(f"too many files: {len(files)} > {MAX_FILES}")
    
    total_bytes = 0
    for i, f in enumerate(files):
        path = f.get("path", "")
        
        # Normalize path
        normalized = os.path.normpath(path).lstrip('/')
        
        # Check for absolute path before normalization
        if path.startswith("/") or re.match(r"^[a-zA-Z]:", path):
            errors.append(f"file[{i}] absolute path denied: {path}")
            continue

        # Check deny patterns
        for pattern in DENY_PATTERNS:
            if pattern.search(normalized):
                errors.append(f"file[{i}] path denied: {path}")
                break
        
        # Check patch size
        patch = f.get("patch", "")
        if isinstance(patch, str):
            patch_bytes = len(patch.encode('utf-8'))
        else:
            patch_bytes = 0
            errors.append(f"file[{i}] patch must be string")
        
        total_bytes += patch_bytes
        if patch_bytes > MAX_FILE_BYTES:
            errors.append(f"file[{i}] patch too large: {patch_bytes} > {MAX_FILE_BYTES}")
    
    if total_bytes > MAX_PATCH_BYTES:
        errors.append(f"total patch too large: {total_bytes} > {MAX_PATCH_BYTES}")
    
    # commit_message
    msg = request.get("commit_message", "")
    if not msg:
        errors.append("commit_message must be non-empty")
    else:
        # Must start with model prefix
        prefix_map = {"GPT 5.6": "[GPT-5.6]", "qwen3.8-max": "[qwen3.8-max]", "GLM 5.2": "[GLM-5.2]"}
        expected_prefix = prefix_map.get(model, "")
        if expected_prefix and not msg.startswith(expected_prefix):
            errors.append(f"commit_message must start with '{expected_prefix}'")
    
    # required_checks
    checks = request.get("required_checks", [])
    if not isinstance(checks, list):
        errors.append("required_checks must be a list")
    
    valid = len(errors) == 0
    normalized = None
    if valid:
        normalized = {
            "schema": SCHEMA,
            "request_id": rid,
            "target_repo": TARGET_REPO,
            "author_model": model,
            "base_sha": base_sha,
            "target_branch": f"automation/{model.replace(' ', '-').lower()}/{rid}",
            "operation": op,
            "files": [{"path": os.path.normpath(f["path"]).lstrip('/'), "patch": f["patch"]} for f in files],
            "commit_message": msg,
            "required_checks": checks,
        }
    
    return valid, errors, normalized


def main():
    if len(sys.argv) < 2:
        print("Usage: validate_write_request.py <request.json>")
        sys.exit(1)
    
    with open(sys.argv[1]) as f:
        request = json.load(f)
    
    valid, errors, normalized = validate(request)
    
    if valid:
        print("VALID")
        print(json.dumps(normalized, indent=2))
        sys.exit(0)
    else:
        print("INVALID")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
