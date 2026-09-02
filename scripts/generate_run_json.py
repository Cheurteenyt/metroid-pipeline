#!/usr/bin/env python3
import json, os, datetime, hashlib

def ge(k, d=""):
    return os.environ.get(k, d)

def gi(k, d=0):
    try:
        return int(os.environ.get(k, str(d)))
    except:
        return d

te = gi("TESTS_EXPECTED")
tf = gi("TESTS_FOUND")
tx = gi("TESTS_EXECUTED")
tp = gi("TESTS_PASSED")
tfl = gi("TESTS_FAILED")
tm = gi("TESTS_MISSING")
sm = ge("SOURCE_SHA_MATCH", "false").lower() == "true"

s = "FAIL"
if tm == 0 and tfl == 0 and tx == te and te > 0 and sm:
    s = "PASS"

rid = ge("REQUEST_ID")
if not rid:
    rid = f"failed-{os.environ.get('GITHUB_RUN_ID', 'unknown')}"

pd = f"proof/{rid}"
os.makedirs(pd, exist_ok=True)

capstone_version = ge("CAPSTONE_VERSION", "unknown")
pytest_version = ge("PYTEST_VERSION", "unknown")
python_version = ge("PYTHON_VERSION", "unknown")

proof_files = []
for root, dirs, files in os.walk(pd):
    for file in files:
        if file != "run.json":
            filepath = os.path.join(root, file)
            proof_files.append(filepath)

proof_content = b""
for filepath in sorted(proof_files):
    with open(filepath, 'rb') as f:
        proof_content += f.read()

proof_sha256 = hashlib.sha256(proof_content).hexdigest()

data = {
    "request_id": rid,
    "runner_repo": "Cheurteenyt/metroid-pipeline",
    "runner_commit": ge("GITHUB_SHA"),
    "trigger_commit": ge("GITHUB_SHA"),
    "source_repo": "gitlab.com/cheurteen/metroid",
    "requested_source_commit": ge("REQUESTED_SOURCE_COMMIT"),
    "checked_out_source_commit": ge("CHECKED_OUT_SOURCE_COMMIT"),
    "source_sha_match": sm,
    "profile": ge("PROFILE"),
    "runner_os": "ubuntu-latest",
    "dependencies": {
        "capstone": capstone_version,
        "pytest": pytest_version,
        "python": python_version
    },
    "timestamp_utc": datetime.datetime.utcnow().isoformat() + "Z",
    "status": s,
    "tests_expected": te,
    "tests_found": tf,
    "tests_executed": tx,
    "tests_passed": tp,
    "tests_failed": tfl,
    "tests_missing": tm,
    "fail_reason": ge("FAIL_REASON"),
    "proof_sha256": proof_sha256,
    "commands": [
        "git clone git@gitlab.com:cheurteen/metroid.git",
        "git checkout " + ge("REQUESTED_SOURCE_COMMIT"),
        "PYTHONPATH=/tmp/metroid/switch/scripts pytest switch/scripts/test_*.py"
    ]
}

with open(os.path.join(pd, "run.json"), "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")

print(json.dumps(data, indent=2))
print(f"\n{'='*50}\nFINAL STATUS: {s}\n{'='*50}")
