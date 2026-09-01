#!/usr/bin/env python3
import json, os, sys, glob
rid=os.environ.get("REQUEST_ID","")
if not rid: rid=f"failed-{os.environ.get('GITHUB_RUN_ID','unknown')}"
path=f"proof/{rid}/run.json"
if not os.path.exists(path):
    paths=glob.glob("proof/*/run.json")
    if not paths: print(f"::error::No run.json at {path}"); sys.exit(1)
    path=paths[0]
try:
    with open(path) as f: data=json.load(f)
    s=data.get("status","FAIL")
    print(f"run.json status: {s}")
    if s!="PASS":
        print(f"::error::Status is {s} ({data.get('fail_reason','')})"); sys.exit(1)
    print("PASS confirmed")
except json.JSONDecodeError as e:
    print(f"::error::Invalid JSON: {e}"); sys.exit(1)
except Exception as e:
    print(f"::error::Cannot read: {e}"); sys.exit(1)
