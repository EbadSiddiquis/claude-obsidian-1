#!/usr/bin/env python3
"""ingest.py - build the Compliance Oracle DB: fetch the custody-triad authorities from eCFR
(live, pinned to current amendment dates), seed the cross-sovereign graph edges, and load the
exemplar control -> WSP -> system-control chain for investor-fund custody.

THE SLICE (deliberately the smallest complete cross-sovereign example - the highest-risk portal
function, spanning three sovereigns):
  - 17 CFR 227.300(c)/227.303(e)  SEC: funding portal may NOT hold investor funds; qualified third party
  - 12 CFR 330.5 / 330.7          FDIC: pass-through deposit insurance (custodial titling + records)
  - 31 CFR 1023.210               FinCEN: AML program requirement for the BD custodian

Everything is fetched from the golden source (ecfr.gov versioner API) at ingest time - section
titles and amendment dates are read live, never hardcoded from memory.

USAGE
  export SEC_CONTACT_EMAIL="you@example.com"
  python3 ingest.py            # creates/refreshes oracle.db next to this script
"""
import json
import os
import sqlite3
import subprocess
import sys
import urllib.request
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "oracle.db")
CONTACT = os.environ.get("SEC_CONTACT_EMAIL", "set-SEC_CONTACT_EMAIL@example.com")
UA = f"compliance-oracle {CONTACT}"

# The ingestion manifest: (eCFR title, part, sovereign, sections we cite).
# Add a row per (title, part) as the obligation surface grows - one fetch covers a whole part.
MANIFEST = [
    (17, 227, "federal-sec", ["227.300", "227.303"]),
    (12, 330, "fdic",        ["330.5", "330.7"]),
    (31, 1023, "fincen",     ["1023.210"]),
]


def fetch_versions(title: int, part: int) -> list:
    url = f"https://www.ecfr.gov/api/versioner/v1/versions/title-{title}.json?part={part}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r).get("content_versions", [])


def latest_by_section(versions: list) -> dict:
    """{identifier: {amendment_date, name}} taking the LATEST amendment per section."""
    out = {}
    for v in versions:
        ident = v.get("identifier")
        if not ident:
            continue
        cur = out.get(ident)
        if cur is None or (v.get("amendment_date") or "") > (cur.get("amendment_date") or ""):
            out[ident] = v
    return out


def node_id(title: int, section: str) -> str:
    return f"cfr-{title}-{section}"


def main():
    fresh = not os.path.exists(DB)
    con = sqlite3.connect(DB)
    con.executescript(open(os.path.join(HERE, "schema.sql"), encoding="utf-8").read())

    # ── Graph nodes: live-pinned CFR sections across the three sovereigns ──
    today = date.today().isoformat()
    for title, part, sovereign, sections in MANIFEST:
        latest = latest_by_section(fetch_versions(title, part))
        for sec in sections:
            v = latest.get(sec)
            if not v:
                sys.exit(f"ingest: section {sec} not found in eCFR title {title} part {part} - "
                         "the manifest cites a section the golden source does not have. Fix the cite.")
            con.execute(
                "INSERT OR REPLACE INTO nodes (id, kind, tier, sovereign, citation, title, "
                "pinned_version, version_source, source_url, fetched_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (node_id(title, sec), "rule", "A", sovereign, f"{title} CFR {sec}",
                 v.get("name"), v.get("amendment_date"), "ecfr",
                 f"https://www.ecfr.gov/current/title-{title}/section-{sec}", today))
            print(f"  node {node_id(title, sec):22} pinned {v.get('amendment_date')}  {v.get('name', '')[:60]}")

    # ── Cross-sovereign edges: the joins that make this a GRAPH, not a list ──
    EDGES = [
        ("cfr-17-227.303", "cfr-12-330.5", "cross_references",
         "SEC requires a qualified third party (bank/BD) to hold investor funds; FDIC pass-through "
         "insurance is what protects those pooled investor funds at a bank - the account must satisfy "
         "the pass-through requirements or investors lose per-investor coverage."),
        ("cfr-12-330.5", "cfr-12-330.7", "cross_references",
         "General pass-through requirements (titling + records disclose custodial capacity and "
         "ascertainable ownership) applied to accounts held by agents/custodians."),
        ("cfr-17-227.303", "cfr-31-1023.210", "cross_references",
         "If the qualified third party is a registered broker-dealer, it carries FinCEN's AML-program "
         "obligation - the BSA leg of the same custody structure."),
        ("cfr-17-227.300", "cfr-17-227.303", "cross_references",
         "227.300(c) prohibits the portal from holding/handling investor funds; 227.303(e) supplies "
         "the compliant structure (direct transmission to a qualified third party)."),
    ]
    for src, dst, rel, note in EDGES:
        con.execute("INSERT OR REPLACE INTO edges (src, dst, rel, note) VALUES (?,?,?,?)",
                    (src, dst, rel, note))
    print(f"  {len(EDGES)} cross-sovereign edges")

    # ── Exemplar relational chain: obligation -> WSP (candidate) -> system control ──
    con.execute(
        "INSERT OR REPLACE INTO controls (id, obligation, sovereign, severity, cadence, locus, owner, eval_key, state) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        ("oracle_custody_qualified_third_party",
         "Investor funds are transmitted directly to and held by a qualified third party (registered "
         "broker-dealer or bank); the portal never holds, handles, or has access to investor funds; the "
         "custodial account preserves FDIC pass-through insurance; the BD custodian maintains an AML program.",
         "federal-sec+fdic+fincen", "gate_fatal", "continuous", "hybrid", "portal",
         "custody_check", "open"))
    for nid in ("cfr-17-227.300", "cfr-17-227.303", "cfr-12-330.5", "cfr-12-330.7", "cfr-31-1023.210"):
        pv = con.execute("SELECT pinned_version FROM nodes WHERE id=?", (nid,)).fetchone()[0]
        con.execute("INSERT OR REPLACE INTO control_authorities (control_id, node_id, pinned_version) VALUES (?,?,?)",
                    ("oracle_custody_qualified_third_party", nid, pv))

    con.execute(
        "INSERT OR REPLACE INTO wsp_procedures (id, control_id, status, who, what, when_, supervised_by, evidence_artifact) "
        "VALUES (?,?,?,?,?,?,?,?)",
        ("wsp-custody-001", "oracle_custody_qualified_third_party", "candidate",
         "Operations lead",
         "CANDIDATE (pending principal adoption). (1) All investor payments route directly from the "
         "investor to the qualified third-party custodian named in the portal's Form Funding Portal - "
         "never through any portal-controlled account [17 CFR 227.303(e), 227.300(c)]. (2) The custodial "
         "account is titled to disclose the custodial/agency capacity, and a per-investor sub-ledger of "
         "actual ownership is maintained and reconciled, preserving FDIC pass-through coverage "
         "[12 CFR 330.5, 330.7]. (3) Funds release only on offering close (to issuer) or cancellation "
         "(back to investor). (4) Verify annually that the BD custodian maintains its AML program "
         "[31 CFR 1023.210] and remains a registered BD (files X-17A-5 on EDGAR).",
         "Continuous (per transaction) + annual custodian verification",
         "Designated supervisory principal",
         "Custodian agreement; per-investor sub-ledger reconciliation log; annual custodian X-17A-5 evidence")
    )
    con.execute(
        "INSERT OR REPLACE INTO system_controls (id, control_id, spec, check_cmd) VALUES (?,?,?,?)",
        ("sys-custody-001", "oracle_custody_qualified_third_party",
         "Payment flow MUST be investor->custodian direct (no portal-touched account, no portal API key "
         "with withdrawal scope). Ledger service maintains per-investor ownership records against the "
         "custodial account (FDIC pass-through evidence). Release requires close/cancel event + dual "
         "control. Monitor: portal's own CFPORTAL filing names a custodian distinct from the portal; "
         "custodian's X-17A-5 current on EDGAR.",
         "python3 ../scripts/fund-custody-check.py --portal-cik <CIK> --json"))
    print("  exemplar chain: control -> WSP candidate -> system control")

    con.commit()
    con.close()
    print(f"\n{'created' if fresh else 'refreshed'} {DB}")


if __name__ == "__main__":
    main()
