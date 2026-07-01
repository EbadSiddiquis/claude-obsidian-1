#!/usr/bin/env python3
"""authority-drift.py - detect when an authority node's version changed since we pinned it.

Operationalizes the authority-model drift rule: a node's version changes -> the change
PROPAGATES along edges to every control that cites the node (authority_refs), which is flagged
stale -> re-verify -> escalate to counsel. NEVER concludes "non-compliant"; a stale flag means
"the legal basis moved; re-check."

For `version_source: ecfr` nodes, fetches the current eCFR amendment_date for the section and
compares to `pinned_version`. `manual` nodes report "unverified (manual source)".

USAGE
  python3 scripts/authority-drift.py
  python3 scripts/authority-drift.py --json
  python3 scripts/authority-drift.py --registry /path/to/registry.json   # for testing
"""
import argparse
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTROLS_DIR = os.path.join(os.path.dirname(HERE), "controls")
UA = os.environ.get("EDGAR_USER_AGENT", "claude-obsidian-research " + os.environ.get("SEC_CONTACT_EMAIL", "set-SEC_CONTACT_EMAIL@example.com"))


def _ecfr_part(title, part, _cache={}):
    key = (title, part)
    if key not in _cache:
        url = f"https://www.ecfr.gov/api/versioner/v1/versions/title-{title}.json?part={part}"
        out = subprocess.run(["curl", "-sSL", "-A", UA, url], capture_output=True, text=True)
        if out.returncode != 0:
            _cache[key] = None
        else:
            try:
                _cache[key] = json.loads(out.stdout)
            except json.JSONDecodeError:
                _cache[key] = None
    return _cache[key]


def current_ecfr_version(node):
    """Latest eCFR amendment_date for the node's section, or None if unverifiable."""
    section = node.get("ecfr_section", "")
    title = node.get("ecfr_title", 17)
    part = section.split(".")[0] if "." in section else section
    data = _ecfr_part(title, part)
    if not data:
        return None
    latest = ""
    for v in data.get("content_versions", []):
        if v.get("identifier") == section:
            ad = v.get("amendment_date") or ""
            if ad > latest:
                latest = ad
    return latest or None


def affected_controls(node_id):
    hits = []
    for path in glob.glob(os.path.join(CONTROLS_DIR, "*.json")):
        if os.path.basename(path) == "authorities.json":
            continue
        fw = json.load(open(path, encoding="utf-8"))
        for c in fw.get("controls", []):
            if node_id in (c.get("authority_refs") or []):
                hits.append(f"{os.path.basename(path)}::{c['id']}")
    return hits


def main():
    ap = argparse.ArgumentParser(description="Detect authority drift (version change -> stale dependent controls).")
    ap.add_argument("--registry", default=os.path.join(CONTROLS_DIR, "authorities.json"))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    nodes = json.load(open(args.registry, encoding="utf-8"))["authorities"]
    results = []
    for n in nodes:
        if n.get("version_source") == "ecfr":
            cur = current_ecfr_version(n)
            if cur is None:
                status = "unverifiable"
            elif cur == n["pinned_version"]:
                status = "unchanged"
            else:
                status = "DRIFTED"
            results.append({"id": n["id"], "status": status, "pinned": n["pinned_version"],
                            "current": cur, "affected": affected_controls(n["id"]) if status == "DRIFTED" else []})
        else:
            results.append({"id": n["id"], "status": "unverified-manual", "pinned": n["pinned_version"],
                            "current": None, "affected": []})

    drifted = [r for r in results if r["status"] == "DRIFTED"]
    if args.json:
        print(json.dumps({"results": results, "drifted_count": len(drifted)}, indent=2))
        return

    print(f"Authority drift check | {len(nodes)} nodes | DRIFTED: {len(drifted)}\n")
    for r in results:
        line = f"  [{r['status']:>16}] {r['id']}  pinned={r['pinned']}"
        if r["status"] == "DRIFTED":
            line += f"  ->  current={r['current']}"
        print(line)
        for a in r["affected"]:
            print(f"        stale -> re-verify -> escalate: {a}")
    if drifted:
        print(f"\n{len(drifted)} authority node(s) DRIFTED. Dependent controls flagged stale: re-verify against the new text; counsel opines. (No 'non-compliant' conclusion is drawn.)")
    else:
        print("\nNo drift: every auto-checkable authority matches its pinned version. (Manual nodes need human review.)")


if __name__ == "__main__":
    main()
