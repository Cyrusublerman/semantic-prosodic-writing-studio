#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = ROOT / "ASSURANCE_GATE.json"
ALLOWED_STATUSES = {
    "pending",
    "drafted",
    "workflow_configured",
    "partially_configured",
    "pending_external_action",
    "pending_owner_decision",
    "satisfied",
    "waived",
}
NON_WAIVABLE = {
    "integrity",
    "privacy",
    "deletion_honesty",
    "provenance_survival",
    "compatibility_claims",
}


def load_gate() -> dict:
    data = json.loads(GATE_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("assurance gate root must be an object")
    return data


def validate_structure(data: dict) -> list[str]:
    errors: list[str] = []
    gates = data.get("gates")
    if not isinstance(gates, list) or not gates:
        return ["gates must be a non-empty array"]

    seen: set[str] = set()
    for index, gate in enumerate(gates):
        where = f"gates[{index}]"
        if not isinstance(gate, dict):
            errors.append(f"{where} must be an object")
            continue
        gate_id = gate.get("id")
        if not isinstance(gate_id, str) or not gate_id:
            errors.append(f"{where}.id must be a non-empty string")
        elif gate_id in seen:
            errors.append(f"duplicate gate id: {gate_id}")
        else:
            seen.add(gate_id)
        if gate.get("status") not in ALLOWED_STATUSES:
            errors.append(f"{gate_id or where}: unsupported status {gate.get('status')!r}")
        for key in ("required_for_phase6", "required_for_stable"):
            if not isinstance(gate.get(key), bool):
                errors.append(f"{gate_id or where}.{key} must be boolean")
        if gate.get("status") == "satisfied" and not gate.get("evidence"):
            errors.append(f"{gate_id or where}: satisfied gates require evidence")
        if gate.get("status") == "waived" and not gate.get("waiver"):
            errors.append(f"{gate_id or where}: waived gates require a waiver record")

    configured_non_waivable = set(data.get("rules", {}).get("waivers_forbidden_for", []))
    if configured_non_waivable != NON_WAIVABLE:
        errors.append("non-waivable assurance classes were altered")
    return errors


def blocking_gates(data: dict, target: str) -> list[str]:
    field = "required_for_phase6" if target == "phase6" else "required_for_stable"
    blocked: list[str] = []
    for gate in data["gates"]:
        if gate[field] and gate["status"] != "satisfied":
            blocked.append(f"{gate['id']}: {gate['title']} [{gate['status']}]")
    return blocked


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require", choices=("phase6", "stable"))
    args = parser.parse_args()

    data = load_gate()
    errors = validate_structure(data)
    if errors:
        raise SystemExit("Invalid ASSURANCE_GATE.json:\n- " + "\n- ".join(errors))

    if args.require:
        blocked = blocking_gates(data, args.require)
        if blocked:
            raise SystemExit(
                f"{args.require} assurance gate is blocked:\n- " + "\n- ".join(blocked)
            )

    print(
        json.dumps(
            {
                "ok": True,
                "target": args.require or "structure",
                "gate_count": len(data["gates"]),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
