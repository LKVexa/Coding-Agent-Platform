"""Read-only adapter around the unchanged D0001 C0081-03 fixture.

Only baseline and an explicitly faulty all-token-count mutation control are
supported. This program does not execute the legacy product runner or write
to legacy delivery locations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
COMPONENT_ID = "D0001/C0081-03"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def verify_snapshot():
    manifest = load_json(ROOT / "SOURCE-MANIFEST.json")
    for record in manifest["files"]:
        path = (ROOT / record["path"]).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            raise ValueError("invalid or absent pinned snapshot file")
        if hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
            raise ValueError("pinned snapshot digest mismatch: " + record["path"])


def run(case):
    verify_snapshot()
    sys.path.insert(0, str(ROOT / "vendor"))
    import numpy as np
    from d0001 import frog, pairs_c

    if case == "negative-control":
        # Authored mutation control, deliberately incorrect: counts masked roles
        # and accepts unknown roles. Original snapshot bytes remain untouched.
        frog.assistant_token_count = lambda roles: len(roles)
    pair = pairs_c.C0081_03()
    records = {
        "id": pair.id,
        "work_type": pair.work_type,
        "checks": {check["id"]: check for check in pair.checks},
        "records": pair.records,
        "iterations": pair.iterations,
        "repair_log": pair.repair_log,
    }
    historical = load_json(ROOT / "historical" / "records.json")
    comparable = {key: historical[key] for key in records}
    matches = records == comparable
    checks = [
        {
            "id": check["id"],
            "status": check["result"],
            "expected": check["expected"],
            "actual": check["observed"],
            "description": check["description"],
        }
        for check in pair.checks
    ]
    if case == "baseline":
        checks.append({
            "id": "historical_semantic_match",
            "status": "pass" if matches else "fail",
            "expected": True,
            "actual": matches,
            "description": "Original checks, records, iterations and repair log match; runtime fingerprint is recorded separately.",
        })
    candidate_checks = list(checks)
    candidate_accepted = all(check["status"] == "pass" for check in candidate_checks)
    if case == "negative-control":
        checks = [{
            "id": "negative_control_rejected",
            "status": "pass" if not candidate_accepted else "fail",
            "expected": True,
            "actual": not candidate_accepted,
            "description": "The original evaluator rejects an intentionally faulty all-token counter; candidate failures remain in records.",
        }]
    return {
        "schema_version": "1.0.0",
        "component_id": COMPONENT_ID,
        "adapter_version": "0.1.0",
        "case": case,
        "scope": "authored_fixture",
        "execution": "pass",
        "scientific_validation": "unverified",
        "validation_target": "original_fixture" if case == "baseline" else "negative_control_detection",
        "candidate_accepted": candidate_accepted,
        "checks": checks,
        "candidate_checks": candidate_checks,
        "metrics": {
            "check_pass": sum(c["status"] == "pass" for c in checks),
            "check_fail": sum(c["status"] == "fail" for c in checks),
        },
        "historical_comparison": {
            "semantic_match": matches,
            "fields": list(records),
            "excluded_fields": ["fingerprint_inputs"],
            "reason": "Source fingerprints and historical runtime are preserved in the pinned records; the current runtime differs.",
        },
        "runtime": {"python": sys.version.split()[0], "numpy": np.__version__},
        "records": records,
        "limitations": [
            "Bounded authored token-role fixture; not a coding-agent training result or paper-scale validation.",
            "Negative control changes the in-memory counting function only and is intentionally incorrect.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=("baseline", "negative-control"), default="baseline")
    args = parser.parse_args()
    try:
        result = run(args.case)
    except Exception as exc:
        result = {
            "schema_version": "1.0.0", "component_id": COMPONENT_ID,
            "scope": "authored_fixture", "execution": "fail", "checks": [],
            "metrics": {}, "records": {},
            "error": {"type": type(exc).__name__, "message": str(exc)},
        }
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 2
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
