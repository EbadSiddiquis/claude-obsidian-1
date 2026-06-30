"""counsel.py - the named-counsel terminal node (authority-model Tier E).

An opinion-of-record is the ONLY authority that can *close* a judgment call: it converts a
control from escalate_to_counsel/open into `satisfied_by_counsel`, attributed to a named
attorney as of a date. Critically it **decays**: if any authority it relied on drifts
(law-drift, via the registry's pinned_version) or any fact it relied on changes (fact-drift),
the opinion goes STALE and the control reverts to escalate_to_counsel ("re-opine").

The system never opines. It records that a named human opined, and detects when that opinion
is no longer current. See docs/authority-model.md.
"""
import json


def load_opinions(path):
    return json.load(open(path, encoding="utf-8")).get("opinions", [])


def opinion_status(op, registry, current_facts=None):
    """fresh unless a relied-on authority's pinned_version moved, or a relied-on fact changed."""
    stale_law = [aid for aid, v in (op.get("pinned_authority_versions") or {}).items()
                 if aid in registry and registry[aid].get("pinned_version") != v]
    cf = current_facts or {}
    stale_fact = [k for k, v in (op.get("pinned_facts") or {}).items()
                  if cf.get(k) is not None and cf.get(k) != v]
    return {"fresh": not stale_law and not stale_fact, "stale_law": stale_law, "stale_fact": stale_fact}


def apply_opinions(rows, opinions, registry, current_facts=None):
    """Mutate control rows: a fresh opinion -> satisfied_by_counsel (attributed); a stale one ->
    escalate_to_counsel with the decay reason. Returns the rows."""
    by_control = {}
    for op in opinions:
        st = opinion_status(op, registry, current_facts)
        for cid in op.get("covers_controls", []):
            by_control[cid] = (op, st)
    for r in rows:
        hit = by_control.get(r["id"])
        if not hit:
            continue
        op, st = hit
        attribution = {"id": op.get("id"), "attorney": op.get("attorney"), "date": op.get("date"), "fresh": st["fresh"]}
        if st["fresh"]:
            r["state"] = "satisfied_by_counsel"
            r["opinion"] = attribution
        else:
            reasons = []
            if st["stale_law"]:
                reasons.append("law drift: " + ", ".join(st["stale_law"]))
            if st["stale_fact"]:
                reasons.append("fact drift: " + ", ".join(st["stale_fact"]))
            reason = "; ".join(reasons)
            r["state"] = "escalate_to_counsel"
            r["opinion"] = {**attribution, "stale_reason": reason}
            r["note"] = f"Opinion {op.get('id')} STALE ({reason}) - re-opine. " + r.get("note", "")
    return rows
