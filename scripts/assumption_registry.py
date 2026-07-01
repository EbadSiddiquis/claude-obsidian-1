"""assumption_registry.py - load the system-assumption meta-nodes; link them to controls.

See controls/assumptions.json and docs/authority-model.md (Tier F).
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY = os.path.join(os.path.dirname(HERE), "controls", "assumptions.json")


def load_assumptions(path=REGISTRY):
    return json.load(open(path, encoding="utf-8")).get("assumptions", [])


def for_control(assumptions, control_id):
    """Assumptions that could corrupt this control ('*' = all Form-D-driven controls)."""
    out = []
    for a in assumptions:
        ac = a.get("affects_controls") or []
        if "*" in ac or control_id in ac:
            out.append(a)
    return out
