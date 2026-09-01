#!/usr/bin/env python3
import json, sys
request_file = sys.argv[1] if len(sys.argv) > 1 else ""
if not request_file:
    print("REQUEST_ID=\nREQUESTED_SOURCE_COMMIT=\nPROFILE=\nSOURCE_REPO=")
    sys.exit(0)
try:
    with open(request_file) as f:
        d = json.load(f)
    print(f"REQUEST_ID={d.get('request_id', '')}")
    print(f"REQUESTED_SOURCE_COMMIT={d.get('source_commit', '')}")
    print(f"PROFILE={d.get('profile', '')}")
    print(f"SOURCE_REPO={d.get('source_repo', '')}")
except Exception:
    print("REQUEST_ID=\nREQUESTED_SOURCE_COMMIT=\nPROFILE=\nSOURCE_REPO=")
