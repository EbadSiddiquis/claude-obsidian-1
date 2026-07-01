#!/usr/bin/env python3
"""screen-offering.py - focused flow: Form D -> covered persons -> bad-actor monitor.

The lightweight view (just the 506(d) covered persons + their bad-actor drift state). For the
full checklist, use control-panel.py. Shared Form D logic lives in edgar_formd.py.

Never-opine: covered persons + escalate_to_counsel / open + notes; counsel opines.

USAGE
  export SEC_CONTACT_EMAIL="you@example.com"
  python3 scripts/screen-offering.py --cik 2141182
  python3 scripts/screen-offering.py --cik 2141182 --json
"""
import argparse
import json
import os
import subprocess
import sys

import edgar_formd as efd

HERE = os.path.dirname(os.path.abspath(__file__))


def run_badactor(names):
    if not names:
        return {"feed_items": 0, "results": []}
    out = subprocess.run(
        ["python3", os.path.join(HERE, "badactor-watch.py"), "--names", "; ".join(names), "--json"],
        capture_output=True, text=True, env={**os.environ})
    if out.returncode != 0:
        sys.exit(f"badactor-watch failed ({out.returncode}): {out.stderr.strip()}")
    return json.loads(out.stdout)


def main():
    ap = argparse.ArgumentParser(description="Screen a Reg D offering's covered persons against the bad-actor feed (never-opine).")
    ap.add_argument("--cik", required=True, help="issuer CIK (leading zeros optional)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    fd = efd.load_form_d(args.cik)
    people = fd["related_persons"]
    watchlist = [fd["issuer"]] + [p["name"] for p in people]
    screen = run_badactor(watchlist)
    by_name = {r["watch_name"]: r for r in screen["results"]}

    if args.json:
        print(json.dumps({"issuer": fd["issuer"], "cik": str(int(args.cik)), "form_d_accession": fd["accession"],
                          "covered_persons": people, "ap_feed_items": screen.get("feed_items"),
                          "screen": screen["results"]}, indent=2))
        return

    flags = [r for r in screen["results"] if r["state"] == "escalate_to_counsel"]
    print(f"Offering screen | issuer: {fd['issuer']} | CIK {int(args.cik)} | Form D {fd['accession']}")
    print(f"covered persons (incl. issuer): {len(watchlist)} | flagged for counsel: {len(flags)} | conclusions drawn: 0\n")
    for name in watchlist:
        r = by_name.get(name, {"state": "open", "evidence": [], "note": ""})
        rel = next((", ".join(p["relationships"]) for p in people if p["name"] == name), "Issuer entity")
        mark = "FLAG -> counsel" if r["state"] == "escalate_to_counsel" else "open"
        print(f"[{mark}] {name}  ({rel or 'related person'})")
        for ev in r["evidence"]:
            print(f"    - {ev['date'][:16]} | {ev['title'][:88]}")
        if r["note"]:
            print(f"    {r['note']}")
    print("\nScope note: Rule 506(d) covers only certain persons (officers, directors, 20%+ holders,")
    print("promoters, compensated solicitors). Confirm coverage + the disqualifying-event look-back with counsel.")
    print("This screen assembles and flags. It never concludes. Counsel opines.")


if __name__ == "__main__":
    main()
