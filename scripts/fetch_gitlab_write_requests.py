#!/usr/bin/env python3
"""Fetch github-write requests from the GitLab source-of-truth repo.

READ-ONLY towards GitLab (architecture rule: the runner never writes to
GitLab). Authentication, in order:
  1. GITLAB_SSH_KEY_B64  (base64 OpenSSH deploy key — preferred)
  2. GITLAB_TOKEN        (HTTPS oauth2 — legacy smoke convention)
  3. anonymous HTTPS     (only works if the project is public)

Modes:
  * default: shallow-clone (or refresh) the repo into --dest and export
    every requests/github-write/*.json into --dest with a manifest JSON
    (gitlab_head_sha, per-file sha256, best-effort request_id).
  * --ls-remote-only --expected-head <sha>: cheap change detection; exits 0
    with {"unchanged": true} when the remote head still equals <sha>.

Output: manifest JSON on stdout and (optionally) --manifest-out FILE.
Exit codes: 0 ok, 4 no access, 5 usage error, 6 git failure.
"""
import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# URLs overridable via env for hermetic testing (production default below).
GITLAB_SSH_URL = os.environ.get(
    "GITLAB_SSH_URL_OVERRIDE", "git@gitlab.com:cheurteen/metroid.git")
GITLAB_HTTPS_URL = os.environ.get(
    "GITLAB_HTTPS_URL_OVERRIDE", "https://gitlab.com/cheurteen/metroid.git")
DEFAULT_SUBDIR = "requests/github-write"
EXIT_OK, EXIT_USAGE, EXIT_ACCESS, EXIT_GIT = 0, 5, 4, 6


def run(cmd, env=None, check=True, timeout=300, cwd=None):
    proc = subprocess.run(
        cmd, env=env, cwd=cwd, capture_output=True, text=True,
        timeout=timeout)
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"command failed ({proc.returncode}): {cmd[0]} {cmd[1:3]}...\n"
            f"stderr: {proc.stderr[-500:]}")
    return proc


def build_git_env():
    """Return (env, url) for git access, or (None, None) if no method."""
    env = dict(os.environ)
    key_b64 = os.environ.get("GITLAB_SSH_KEY_B64", "").strip()
    token = os.environ.get("GITLAB_TOKEN", "").strip()

    if key_b64:
        try:
            raw = base64.b64decode(key_b64, validate=False)
            if b"OPENSSH PRIVATE KEY" not in raw and b"PRIVATE KEY" not in raw:
                raise ValueError("decoded payload is not a private key")
            keyfile = tempfile.NamedTemporaryFile(
                prefix="glkey_", suffix=".pem", delete=False)
            keyfile.write(raw)
            keyfile.close()
            os.chmod(keyfile.name, 0o600)
            # Test hook: environments without an ssh binary (e.g. sandboxes)
            # can inject their own GIT_SSH command (e.g. a paramiko wrapper).
            override = os.environ.get("GIT_SSH_COMMAND_OVERRIDE", "")
            env["GIT_SSH_COMMAND"] = override or (
                f"ssh -i {keyfile.name} -o IdentitiesOnly=yes "
                f"-o BatchMode=yes -o StrictHostKeyChecking=accept-new")
            return env, GITLAB_SSH_URL
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(
                f"warn: GITLAB_SSH_KEY_B64 unusable ({exc}); trying fallback\n")

    if token:
        env.pop("GIT_SSH_COMMAND", None)
        url = GITLAB_HTTPS_URL.replace(
            "https://", f"https://oauth2:{token}@")
        return env, url

    env.pop("GIT_SSH_COMMAND", None)
    return env, GITLAB_HTTPS_URL  # anonymous; may work for public projects


def remote_head(env, url):
    proc = run(["git", "ls-remote", "--heads", url, "main"],
               env=env, check=False, timeout=120)
    if proc.returncode != 0 or not proc.stdout.strip():
        raise RuntimeError(f"ls-remote failed: {proc.stderr[-300:]}")
    return proc.stdout.split()[0].strip()


def clone_shallow(env, url, dest):
    dest = Path(dest)
    if dest.exists():
        subprocess.run(["rm", "-rf", str(dest)], check=True)
    run(["git", "clone", "--depth", "1", "--branch", "main",
         url, str(dest)], env=env, timeout=600)


def main(argv):
    args = list(argv[1:])

    def opt(name, default=None):
        if name in args:
            i = args.index(name)
            if i + 1 >= len(args):
                return None
            return args[i + 1]
        return default

    dest = opt("--dest", "/tmp/gitlab-write-requests")
    manifest_out = opt("--manifest-out", "")
    subdir = opt("--subdir", DEFAULT_SUBDIR)
    expected_head = opt("--expected-head", "")
    ls_remote_only = "--ls-remote-only" in args

    if ls_remote_only:
        if expected_head is None:
            print(json.dumps({
                "unchanged": False,
                "error": "--expected-head required"}))
            return EXIT_USAGE
        env, url = build_git_env()
        try:
            head = remote_head(env, url)
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"unchanged": False, "error": str(exc)}))
            return EXIT_ACCESS
        if head == expected_head:
            print(json.dumps({"unchanged": True, "gitlab_head_sha": head}))
            return EXIT_OK
        print(json.dumps({"unchanged": False, "gitlab_head_sha": head}))
        return EXIT_OK

    env, url = build_git_env()
    repo_dir = str(Path(dest) / "repo")
    try:
        clone_shallow(env, url, repo_dir)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"error: cannot clone GitLab repo: {exc}\n")
        print(json.dumps({"ok": False, "error": "clone_failed",
                          "detail": str(exc)[:300], "requests": []}))
        return EXIT_ACCESS

    try:
        head = run(["git", "rev-parse", "HEAD"], cwd=repo_dir).stdout.strip()
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc), "requests": []}))
        return EXIT_GIT

    requests = []
    scan_dir = Path(repo_dir) / subdir
    if scan_dir.is_dir():
        for p in sorted(scan_dir.glob("*.json")):
            try:
                raw = p.read_bytes()
                item = {
                    "file": p.name,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "request_id": "",
                }
                try:
                    data = json.loads(raw.decode("utf-8"))
                    if isinstance(data, dict) and isinstance(
                            data.get("request_id"), str):
                        item["request_id"] = data["request_id"][:64]
                except Exception:  # noqa: BLE001
                    item["malformed"] = True
                dest_copy = Path(dest) / p.name
                dest_copy.write_bytes(raw)
                item["local_copy"] = str(dest_copy)
                requests.append(item)
            except OSError as exc:
                sys.stderr.write(f"warn: cannot read {p}: {exc}\n")

    manifest = {
        "ok": True,
        "gitlab_head_sha": head,
        "subdir": subdir,
        "count": len(requests),
        "requests": requests,
    }
    if manifest_out:
        Path(manifest_out).write_text(
            json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv))
