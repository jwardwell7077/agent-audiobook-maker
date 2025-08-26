import json
import os
import sys
from dataclasses import dataclass
from typing import Any

import requests

LF_URL = os.getenv("LANGFLOW_URL", "http://localhost:7860")
FLOW_ID = os.getenv("LANGFLOW_FLOW_ID")


@dataclass
class RunResult:
    ok: bool
    status: int
    body: dict[str, Any]


def run_flow(flow_id: str, inputs: dict[str, Any] | None = None) -> RunResult:
    url = f"{LF_URL}/api/v1/run/{flow_id}"
    payload = {"inputs": inputs or {}}
    r = requests.post(url, json=payload, timeout=60)
    try:
        body = r.json()
    except Exception:
        body = {"raw": r.text}
    return RunResult(ok=r.ok, status=r.status_code, body=body)


if __name__ == "__main__":
    fid = FLOW_ID or (sys.argv[1] if len(sys.argv) > 1 else None)
    if not fid:
        print("Set LANGFLOW_FLOW_ID or pass FLOW_ID as argv[1]")
        sys.exit(2)

    inputs = {
        "title": "From REST",
        "notes": "Ping from run_flow.py",
        "items": ["x", "y", "z"],
    }
    result = run_flow(fid, inputs)
    print(json.dumps(result.body, indent=2))
    sys.exit(0 if result.ok else 1)
