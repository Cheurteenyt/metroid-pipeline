#!/usr/bin/env python3
"""Apply a VALIDATED github-write-request/v1 to the working tree.

Input: the *normalized* request produced by validate_write_request.py
(paths already allowlisted, sizes already bounded). This script re-checks
the filesystem-level safety anyway (defense in depth):

  - patch  : target MUST already exist (regular file)  -> overwrite content
  - create : target MUST NOT exist                     -> write content
  - delete : target MUST exist (regular file)          -> remove it
  - no symlink may be followed outside the repo root
  - result JSON (paths actually changed) is written for the proof generator
    -- this removes the workflow-level bash bookkeeping entirely.

This script NEVER commits, NEVER pushes, NEVER touches git state.
Exit 0 on success, 4 on refusal/error (result JSON still written).
"""
import json
import os
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_ERROR = 4


def _safe_target(root: Path, relpath: str) -> Path:
    """Resolve target path and guarantee it stays inside root.

    Raises ValueError on escape attempts (symlinks, weird components).
    """
    root = root.resolve()
    target = (root / relpath)
    resolved = target.resolve()
    if resolved == root or root not in resolved.parents:
        raise ValueError(f"path escapes repo root: {relpath}")
    # Refuse any symlinked directory component between root and target.
    cur = root
    for part in Path(relpath).parts[:-1]:
        cur = cur / part
        if cur.is_symlink():
            raise ValueError(f"symlinked parent directory not allowed: {cur}")
    if target.is_symlink():
        raise ValueError(f"symlink target not allowed: {relpath}")
    return target


def apply_request(repo_root: str, normalized: dict) -> dict:
    """Apply the normalized request. Returns a result dict (never raises)."""
    root = Path(repo_root)
    result = {
        "applied": [],
        "applied_paths": [],
        "count": 0,
        "requested_count": len(normalized.get("files", [])),
        "errors": [],
        "ok": False,
    }

    files = normalized.get("files", [])
    operation = normalized.get("operation", "")

    for f in files:
        relpath = f.get("path", "")
        patch = f.get("patch", "")
        op = normalized.get("op_per_file", operation)  # per-request op (v1)
        try:
            target = _safe_target(root, relpath)
            exists = target.exists() and not target.is_symlink()

            if op == "patch":
                if not exists:
                    raise ValueError(
                        f"operation 'patch' requires an existing file: {relpath}")
                if not target.is_file():
                    raise ValueError(
                        f"target is not a regular file: {relpath}")
                target.write_text(patch, encoding="utf-8")
                action = "patched"
            elif op == "create":
                if exists:
                    raise ValueError(
                        f"operation 'create' requires a non-existing file: "
                        f"{relpath}")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(patch, encoding="utf-8")
                action = "created"
            elif op == "delete":
                if not exists:
                    raise ValueError(
                        f"operation 'delete' requires an existing file: "
                        f"{relpath}")
                if not target.is_file():
                    raise ValueError(
                        f"target is not a regular file: {relpath}")
                target.unlink()
                action = "deleted"
            else:
                raise ValueError(f"unknown operation: {op!r}")

            result["applied"].append({
                "path": relpath,
                "operation": op,
                "action": action,
                "bytes": len(patch.encode("utf-8")) if op != "delete" else 0,
            })
            result["applied_paths"].append(relpath)
            result["count"] += 1
        except Exception as exc:  # noqa: BLE001 — fail-closed, capture all
            result["errors"].append(f"{relpath}: {exc}")

    result["ok"] = (
        not result["errors"]
        and result["count"] == result["requested_count"]
    )
    return result


def main(argv):
    args = list(argv[1:])
    result_out = "/tmp/apply_result.json"
    if "--result-out" in args:
        i = args.index("--result-out")
        result_out = args[i + 1]
        del args[i:i + 2]
    if len(args) < 2:
        print(json.dumps({
            "ok": False,
            "errors": ["usage: apply_write_patch.py <repo_root> "
                       "<normalized.json> [--result-out FILE]"],
            "applied": [], "applied_paths": [], "count": 0,
            "requested_count": 0,
        }, indent=2))
        with open(result_out, "w", encoding="utf-8") as fh:
            json.dump({"ok": False, "errors": ["usage error"],
                       "applied": [], "applied_paths": [],
                       "count": 0, "requested_count": 0}, fh)
        return EXIT_ERROR

    repo_root, request_path = args[0], args[1]
    try:
        with open(request_path, "r", encoding="utf-8") as fh:
            normalized = json.load(fh)
        if not isinstance(normalized, dict):
            raise ValueError("normalized request must be a JSON object")
    except Exception as exc:  # noqa: BLE001
        result = {"ok": False, "errors": [f"cannot load request: {exc}"],
                  "applied": [], "applied_paths": [], "count": 0,
                  "requested_count": 0}
        with open(result_out, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2)
        print(json.dumps(result, indent=2))
        return EXIT_ERROR

    result = apply_request(repo_root, normalized)

    with open(result_out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)

    print(json.dumps(result, indent=2))
    if not result["ok"]:
        return EXIT_ERROR

    for item in result["applied"]:
        print(f"  {item['action']}: {item['path']}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv))
