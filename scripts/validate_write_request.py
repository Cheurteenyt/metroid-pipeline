#!/usr/bin/env python3
"""Validate a github-write-request/v1 payload (write relay, v1.1).

Protocol: see docs/WRITE_RELAY_CONTRACT.md.

Output (stdout) is a single JSON object:
  {"valid": true,  "normalized": {...}}
  {"valid": false, "errors": [...], "echo": {"request_id": ..., "author_model": ...}}
  {"valid": false, "malformed": true, "error": "..."}   (unreadable/bad JSON)

Exit codes: 0 = valid, 2 = invalid, 3 = malformed.

The validator is PURE: it never touches the filesystem or network.
Existence/anti-replay/base-SHA checks are the workflow's job (fail-closed there).
"""
import json
import posixpath
import re
import sys

SCHEMA = "github-write-request/v1"
TARGET_REPO = "Cheurteenyt/metroid-pipeline"

# Models allowed to submit requests (mission GPT 5.6 — unchanged)
ALLOWED_MODELS = ("GPT 5.6", "qwen3.8-max", "GLM 5.2")
MODEL_PREFIX = {
    "GPT 5.6": "[GPT-5.6]",
    "qwen3.8-max": "[qwen3.8-max]",
    "GLM 5.2": "[GLM-5.2]",
}
MODEL_SLUG = {
    "GPT 5.6": "gpt-5.6",
    "qwen3.8-max": "qwen3.8-max",
    "GLM 5.2": "glm-5.2",
}

OPERATIONS = ("patch", "create", "delete")
CHECK_WHITELIST = ("python-tests",)  # unknown requirement => REJECT (fail-closed)

# Size limits (documented in the contract)
MAX_FILES = 10
MAX_FILE_BYTES = 10_000
MAX_TOTAL_BYTES = 50_000
MAX_TOTAL_LINES = 2_000
MAX_COMMIT_MSG = 200
MAX_CHECKS = 5

REQUEST_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
BRANCH_RE = re.compile(r"^[a-zA-Z0-9/_.-]{1,100}$")
# Strict allowlist for normalized paths (no colon, no backslash, no space,
# no control chars). Denylist below is defense in depth on top of this.
PATH_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")

# Paths that must NEVER be mutated through the relay.
DENY_PREFIXES = (
    ".github/",   # workflows & repo config: deployable only by human commit
    ".git/",      # internal git state
    "secrets/",   # secret material
    "proof/",     # evidence integrity
    "requests/",  # request lifecycle & anti-replay registry integrity
)
# Gate scripts: the relay must not be able to weaken its own guards.
GATE_FILES = frozenset({
    "scripts/validate_write_request.py",
    "scripts/apply_write_patch.py",
    "scripts/generate_write_proof.py",
    "scripts/test_write_validation.py",
    "scripts/fetch_gitlab_write_requests.py",
    "scripts/check_status.py",
    "scripts/parse_request.py",
    "scripts/generate_run_json.py",
    "scripts/parse_regression_request.py",
    "scripts/generate_regression_run_json.py",
    "scripts/regression_compare.py",
    "scripts/test_regression_negative.py",
})
DENY_EXACT = frozenset({".gitmodules", ".gitlab-ci.yml", ".env"})


def _deny_path(path: str) -> bool:
    """True if the normalized path is forbidden."""
    if path in DENY_EXACT or path in GATE_FILES:
        return True
    for pfx in DENY_PREFIXES:
        if path.startswith(pfx):
            return True
    base = posixpath.basename(path)
    if base.startswith(".env"):
        return True
    if base.endswith(".pem") or base.endswith(".key"):
        return True
    return False


def _normalize_path(raw: str) -> str:
    """Normalize a path; caller must treat '' as invalid."""
    p = posixpath.normpath(raw.strip())
    if p.startswith("./"):
        p = p[2:]
    return p


def validate(request):
    """Validate a request dict.

    Returns (valid, errors, normalized). Never raises on bad shapes.
    """
    errors = []

    if not isinstance(request, dict):
        return False, ["request must be a JSON object"], None

    echo = {
        "request_id": request.get("request_id")
        if isinstance(request.get("request_id"), str) else "",
        "author_model": request.get("author_model")
        if isinstance(request.get("author_model"), str) else "",
    }

    # --- schema (strict) ---------------------------------------------------
    if request.get("schema") != SCHEMA:
        errors.append(f"schema must be exactly '{SCHEMA}'")
        return False, errors, echo  # nothing else can be trusted

    # --- request_id ---------------------------------------------------------
    rid = request.get("request_id")
    if not isinstance(rid, str) or not rid:
        errors.append("request_id must be a non-empty string")
        rid = ""
    elif not REQUEST_ID_RE.fullmatch(rid):
        errors.append(
            "request_id must match [a-zA-Z0-9_-]{1,64}: %r" % rid[:80])
        rid = ""
    elif rid == "unknown":
        errors.append("request_id 'unknown' is reserved")

    # --- target_repo ----------------------------------------------------------
    if request.get("target_repo") != TARGET_REPO:
        errors.append(f"target_repo must be exactly '{TARGET_REPO}'")

    # --- author_model ---------------------------------------------------------
    model = request.get("author_model")
    if model not in ALLOWED_MODELS:
        errors.append(
            "author_model must be one of %s" % (list(ALLOWED_MODELS),))
        model = ""

    # --- base_sha -------------------------------------------------------------
    base_sha = request.get("base_sha")
    if not isinstance(base_sha, str) or not SHA_RE.fullmatch(base_sha):
        errors.append(
            "base_sha must be exactly 40 lowercase hex chars, got %r"
            % (str(base_sha)[:80],))
        base_sha = ""

    # --- target_branch (advisory; real branch is derived) ----------------------
    req_branch = request.get("target_branch", "")
    if req_branch:
        if not isinstance(req_branch, str):
            errors.append("target_branch must be a string")
        elif req_branch in ("main", "master"):
            errors.append("target_branch must not be main/master")
        elif not BRANCH_RE.fullmatch(req_branch) or ".." in req_branch.split("/"):
            errors.append("target_branch contains invalid segments: %r"
                          % req_branch[:80])

    # --- operation -------------------------------------------------------------
    op = request.get("operation")
    if op not in OPERATIONS:
        errors.append("operation must be one of %s, got %r"
                      % (list(OPERATIONS), str(op)[:40]))
        op = ""

    # --- files -------------------------------------------------------------------
    files = request.get("files")
    if not isinstance(files, list) or not files:
        errors.append("files must be a non-empty list")
        files = []
    elif len(files) > MAX_FILES:
        errors.append(f"too many files: {len(files)} > {MAX_FILES}")

    normalized_files = []
    seen_paths = set()
    total_bytes = 0
    total_lines = 0
    if isinstance(files, list):
        for i, f in enumerate(files):
            if not isinstance(f, dict):
                errors.append(f"file[{i}] must be an object")
                continue
            raw_path = f.get("path")
            if not isinstance(raw_path, str) or not raw_path.strip():
                errors.append(f"file[{i}] path must be a non-empty string")
                continue
            if "\\" in raw_path:
                errors.append(
                    f"file[{i}] backslash not allowed in path: {raw_path!r}")
                continue
            if raw_path.startswith("/") or re.match(r"^[A-Za-z]:", raw_path):
                errors.append(f"file[{i}] absolute path denied: {raw_path!r}")
                continue
            norm = _normalize_path(raw_path)
            if norm in ("", ".", "..") or norm.startswith("../"):
                errors.append(f"file[{i}] path escapes repo: {raw_path!r}")
                continue
            if not PATH_RE.fullmatch(norm):
                errors.append(
                    f"file[{i}] path has forbidden characters: {raw_path!r}")
                continue
            if norm.endswith("/"):
                errors.append(f"file[{i}] path must be a file: {raw_path!r}")
                continue
            if _deny_path(norm):
                errors.append(f"file[{i}] path denied by policy: {norm}")
                continue
            if norm in seen_paths:
                errors.append(f"file[{i}] duplicate path: {norm}")
                continue
            seen_paths.add(norm)

            patch = f.get("patch")
            if not isinstance(patch, str):
                errors.append(f"file[{i}] patch must be a string")
                continue
            if "\x00" in patch:
                errors.append(f"file[{i}] patch contains NUL byte")
                continue
            if op == "delete" and patch != "":
                errors.append(f"file[{i}] delete requires empty patch")
                continue

            pb = len(patch.encode("utf-8"))
            pl = patch.count("\n") + 1 if patch else 0
            if pb > MAX_FILE_BYTES:
                errors.append(
                    f"file[{i}] patch too large: {pb} > {MAX_FILE_BYTES} bytes")
                continue
            total_bytes += pb
            total_lines += pl
            normalized_files.append({
                "path": norm,
                "patch": patch,
                "bytes": pb,
                "lines": pl,
            })

    if total_bytes > MAX_TOTAL_BYTES:
        errors.append(
            f"total patch size too large: {total_bytes} > {MAX_TOTAL_BYTES} bytes")
    if total_lines > MAX_TOTAL_LINES:
        errors.append(
            f"total line count too large: {total_lines} > {MAX_TOTAL_LINES}")

    # --- commit_message ------------------------------------------------------------
    msg = request.get("commit_message")
    if not isinstance(msg, str) or not msg.strip():
        errors.append("commit_message must be a non-empty string")
        msg = ""
    else:
        prefix = MODEL_PREFIX.get(model, "")
        if prefix and not msg.startswith(prefix):
            errors.append(
                f"commit_message must start with '{prefix}' for author_model "
                f"'{model}'")
        # Normalize: single line, no control chars, bounded length.
        msg = " ".join(msg.replace("\r", " ").replace("\n", " ").split())
        if len(msg) > MAX_COMMIT_MSG:
            errors.append(
                f"commit_message too long: {len(msg)} > {MAX_COMMIT_MSG}")
            msg = msg[:MAX_COMMIT_MSG]
        if prefix and msg.startswith(prefix):
            subject = msg[len(prefix):].strip()
            if len(subject) < 3:
                errors.append("commit_message needs a subject after the prefix")

    # --- required_checks ----------------------------------------------------------
    checks = request.get("required_checks", [])
    if not isinstance(checks, list):
        errors.append("required_checks must be a list")
        checks = []
    if len(checks) > MAX_CHECKS:
        errors.append(f"too many required_checks: {len(checks)} > {MAX_CHECKS}")
        checks = checks[:MAX_CHECKS]
    clean_checks = []
    for c in checks:
        if not isinstance(c, str) or c not in CHECK_WHITELIST:
            errors.append(
                "required_checks contains unsupported check %r "
                "(allowed: %s) — fail-closed reject" % (c, list(CHECK_WHITELIST)))
        elif c not in clean_checks:
            clean_checks.append(c)

    valid = len(errors) == 0
    normalized = None
    if valid:
        slug = MODEL_SLUG[model]
        normalized = {
            "schema": SCHEMA,
            "request_id": rid,
            "target_repo": TARGET_REPO,
            "author_model": model,
            "model_prefix": MODEL_PREFIX[model],
            "base_sha": base_sha,
            "target_branch": f"automation/{slug}/{rid}",
            "requested_branch_echo": req_branch or "",
            "operation": op,
            "files": normalized_files,
            "commit_message": msg,
            "required_checks": clean_checks,
        }
    return valid, errors, normalized


def _best_effort_echo(payload_text: str) -> dict:
    """Extract request_id/author_model even from partially broken payloads."""
    echo = {"request_id": "", "author_model": ""}
    try:
        d = json.loads(payload_text)
        if isinstance(d, dict):
            if isinstance(d.get("request_id"), str):
                echo["request_id"] = d["request_id"][:64]
            if isinstance(d.get("author_model"), str):
                echo["author_model"] = d["author_model"][:40]
    except Exception:
        pass
    return echo


def main(argv):
    if len(argv) < 2:
        print(json.dumps({
            "valid": False, "malformed": True,
            "error": "usage: validate_write_request.py <request.json>"}))
        return 3
    try:
        with open(argv[1], "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        print(json.dumps({
            "valid": False, "malformed": True, "error": str(exc)}))
        return 3
    try:
        request = json.loads(text)
    except json.JSONDecodeError as exc:
        print(json.dumps({
            "valid": False, "malformed": True,
            "error": f"invalid JSON: {exc}",
            "echo": _best_effort_echo(text)}))
        return 3

    valid, errors, normalized = validate(request)
    if valid:
        print(json.dumps({"valid": True, "normalized": normalized}, indent=2))
        return 0
    print(json.dumps({
        "valid": False,
        "errors": errors,
        "echo": _best_effort_echo(text),
    }, indent=2))
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
