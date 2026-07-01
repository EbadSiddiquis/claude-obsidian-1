#!/usr/bin/env python3
"""fedreg-watch.py - Federal Register drift source (closes the 'binding != codified' gap).

eCFR diff (authority-drift.py) only catches CODIFIED rule-text changes. Binding law also arrives
as SEC final rules, releases, and exemptive ORDERS - and the order may not be in the CFR yet (the
April-2026 tender-offer order is the canonical example). This watcher queries the Federal Register
API for SEC documents published since a date and maps them to authority nodes by CFR part:

  - touches a part we cite (230/227...) -> AFFECTS-NODES -> list dependent controls (potential drift)
  - touches title 17 but not our parts    -> OTHER-SEC-RULE (context)
  - no CFR reference (e.g., an order)      -> UNMAPPED-REVIEW (the binding-but-uncodified catch)

Never concludes. A hit means "new SEC action - review whether it affects these controls; counsel assesses."

USAGE
  python3 scripts/fedreg-watch.py                 # since our newest codified pin
  python3 scripts/fedreg-watch.py --since 2020-01-01 --proposed --notices
  python3 scripts/fedreg-watch.py --json
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
CONTROLS_DIR = os.path.join(os.path.dirname(HERE), "controls")
UA = os.environ.get("EDGAR_USER_AGENT", "claude-obsidian-research " + os.environ.get("SEC_CONTACT_EMAIL", "set-SEC_CONTACT_EMAIL@example.com"))
API = "https://www.federalregister.gov/api/v1/documents.json"


def registry_parts():
    """{cfr_part: [node_id,...]} for federal-sec ecfr nodes, and the newest pinned date."""
    reg = json.load(open(os.path.join(CONTROLS_DIR, "authorities.json")))["authorities"]
    parts, newest = {}, ""
    for n in reg:
        if n.get("version_source") == "ecfr" and n.get("ecfr_section"):
            part = n["ecfr_section"].split(".")[0]
            parts.setdefault(part, []).append(n["id"])
            newest = max(newest, n.get("pinned_version", ""))
    return parts, newest


def controls_citing(node_ids):
    hits = []
    node_ids = set(node_ids)
    for path in glob.glob(os.path.join(CONTROLS_DIR, "*.json")):
        if os.path.basename(path) == "authorities.json":
            continue
        for c in json.load(open(path)).get("controls", []):
            if node_ids & set(c.get("authority_refs") or []):
                hits.append(f"{os.path.basename(path)}::{c['id']}")
    return hits


def fetch(since, types):
    pairs = [("per_page", "100"), ("order", "newest"),
             ("conditions[agencies][]", "securities-and-exchange-commission"),
             ("conditions[publication_date][gte]", since)]
    pairs += [("conditions[type][]", t) for t in types]
    pairs += [("fields[]", f) for f in ("document_number", "title", "type", "publication_date", "cfr_references", "html_url")]
    url = API + "?" + urllib.parse.urlencode(pairs)
    out = subprocess.run(["curl", "-sSL", "-A", UA, url], capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"Federal Register fetch failed: {out.stderr.strip()}")
    return json.loads(out.stdout)


def main():
    ap = argparse.ArgumentParser(description="Federal Register drift watch for SEC actions (never concludes).")
    ap.add_argument("--since", help="publication_date >= (default: newest codified pin in the registry)")
    ap.add_argument("--proposed", action="store_true", help="include proposed rules (PRORULE)")
    ap.add_argument("--notices", action="store_true", help="include notices (orders/exemptive relief often appear here)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    parts_map, newest = registry_parts()
    since = args.since or newest
    types = ["RULE"] + (["PRORULE"] if args.proposed else []) + (["NOTICE"] if args.notices else [])

    data = fetch(since, types)
    results = []
    for r in data.get("results", []):
        parts17 = sorted({str(c.get("part")) for c in (r.get("cfr_references") or []) if str(c.get("title")) == "17"})
        matched = [p for p in parts17 if p in parts_map]
        if matched:
            nodes = sorted({nid for p in matched for nid in parts_map[p]})
            status, affected = "AFFECTS-NODES", controls_citing(nodes)
        elif parts17:
            status, affected = "OTHER-SEC-RULE", []
        else:
            status, affected = "UNMAPPED-REVIEW", []
        results.append({"date": r.get("publication_date"), "type": r.get("type"), "doc": r.get("document_number"),
                        "title": r.get("title"), "parts17": parts17, "status": status,
                        "affected_controls": affected, "url": r.get("html_url")})

    affects = [r for r in results if r["status"] == "AFFECTS-NODES"]
    unmapped = [r for r in results if r["status"] == "UNMAPPED-REVIEW"]
    if args.json:
        print(json.dumps({"since": since, "types": types, "count": data.get("count"),
                          "affects_nodes": len(affects), "unmapped_review": len(unmapped), "results": results}, indent=2))
        return

    print(f"Federal Register watch | SEC | since {since} | types {types} | {data.get('count')} docs | AFFECTS-NODES: {len(affects)} | UNMAPPED-REVIEW: {len(unmapped)}\n")
    for r in results:
        if r["status"] == "OTHER-SEC-RULE":
            continue  # context only; suppress from the default view
        print(f"  [{r['status']}] {r['date']} {r['type']} {r['doc']} parts17={r['parts17'] or 'none'}")
        print(f"      {(r['title'] or '')[:90]}")
        for a in r["affected_controls"]:
            print(f"      review -> may affect: {a}")
    print(f"\n{len(affects)} SEC action(s) touch parts we cite; {len(unmapped)} have no CFR reference (review for binding-but-uncodified, e.g. orders).")
    total = data.get("count") or 0
    if total > len(results):
        print(f"NOTE: showing the newest {len(results)} of {total} matching docs - narrow --since (or paginate) for full coverage.")
    print("Review only - no drift conclusion is drawn. Counsel assesses relevance.")


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        try:
            sys.stdout.close()
        except Exception:
            pass
