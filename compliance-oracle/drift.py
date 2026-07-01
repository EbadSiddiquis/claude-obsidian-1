#!/usr/bin/env python3
"""drift.py - the regulatory-drift monitor for the Oracle DB. Re-fetches every ecfr-sourced node's
current amendment date and, on a version change: (1) flags every control citing that node,
(2) marks every attestation that pinned the old version STALE (fresh=0 -> the WSP reverts to
stale_reattest - the principal must re-adopt). Never concludes; it flags for review.

USAGE
  export SEC_CONTACT_EMAIL="you@example.com"
  python3 drift.py
"""
import json
import os
import sqlite3
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "oracle.db")
UA = f"compliance-oracle {os.environ.get('SEC_CONTACT_EMAIL', 'set-SEC_CONTACT_EMAIL@example.com')}"


def current_amendment(title, section):
    url = f"https://www.ecfr.gov/api/versioner/v1/versions/title-{title}.json?part={section.split('.')[0]}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        best = None
        for v in json.load(r).get("content_versions", []):
            if v.get("identifier") == section:
                d = v.get("amendment_date") or ""
                if best is None or d > best:
                    best = d
        return best


def main():
    con = sqlite3.connect(DB)
    drifted = []
    for nid, citation, pinned in con.execute(
            "SELECT id, citation, pinned_version FROM nodes WHERE version_source='ecfr'"):
        title, section = nid.split("-")[1], nid.split("-", 2)[2]
        cur = current_amendment(int(title), section)
        if cur is None:
            print(f"[unverifiable] {citation}: section not found at eCFR - REVIEW (do not assume unchanged)")
            continue
        if cur != pinned:
            drifted.append((nid, citation, pinned, cur))
            print(f"[DRIFT] {citation}: pinned {pinned} -> current {cur}")
        else:
            print(f"[ ok  ] {citation} @{pinned}")

    for nid, citation, old, new in drifted:
        for (cid,) in con.execute("SELECT control_id FROM control_authorities WHERE node_id=?", (nid,)):
            print(f"    -> control {cid}: cited authority moved - re-verify (state NOT auto-changed; review)")
        stale = con.execute(
            "SELECT a.id, a.wsp_id, a.principal FROM attestations a WHERE a.fresh=1 AND a.pinned_versions LIKE ?",
            (f'%"{nid}"%',)).fetchall()
        for aid, wsp_id, principal in stale:
            con.execute("UPDATE attestations SET fresh=0, stale_reason=? WHERE id=?",
                        (f"{citation} moved {old} -> {new}", aid))
            con.execute("UPDATE wsp_procedures SET status='stale_reattest' WHERE id=?", (wsp_id,))
            print(f"    -> attestation #{aid} by {principal} on {wsp_id}: STALE - re-adopt required")
    con.commit()
    print(f"\n{len(drifted)} drifted node(s). Drift flags for review; nothing auto-resolved.")


if __name__ == "__main__":
    main()
