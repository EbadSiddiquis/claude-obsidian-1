#!/usr/bin/env python3
"""screen-offering.py - first END-TO-END flow: Form D -> covered persons -> bad-actor monitor.

Chains two product atoms into one offering screen:
  1. EDGAR pull: resolve a CIK's latest Form D, fetch its primary_doc.xml, extract the issuer
     and its "related persons" (Rule 506(d) covered persons: executive officers, directors,
     promoters, 20%+ holders, named on the Form D).
  2. badactor-watch.py: run those names through the continuous SEC Administrative Proceedings
     drift check.

THE DISCIPLINE (unchanged): this assembles and flags. It NEVER concludes that an exemption is
lost or that anyone is disqualified. Output is `escalate_to_counsel` / `open` with notes;
counsel opines.

USAGE
  export SEC_CONTACT_EMAIL="you@example.com"
  python3 scripts/screen-offering.py --cik 2141182
  python3 scripts/screen-offering.py --cik 2141182 --json
"""
import argparse
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))


def sec_fetch(url: str) -> str:
    out = subprocess.run(["bash", os.path.join(HERE, "sec-fetch.sh"), url],
                         capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"fetch failed ({out.returncode}) for {url}: {out.stderr.strip()}")
    return out.stdout


def latest_form_d(cik: str):
    """Return (accession, primary_doc) for the most recent Form D, or exit if none."""
    cik10 = str(int(cik)).zfill(10)
    data = json.loads(sec_fetch(f"https://data.sec.gov/submissions/CIK{cik10}.json"))
    issuer = data.get("name", f"CIK {cik}")
    recent = data["filings"]["recent"]
    for form, acc, doc in zip(recent["form"], recent["accessionNumber"], recent["primaryDocument"]):
        if form == "D":
            return issuer, acc, (doc or "primary_doc.xml")
    sys.exit(f"no Form D found for CIK {cik} (issuer: {issuer})")


def form_d_xml(cik: str, accession: str, doc: str) -> str:
    nodash = accession.replace("-", "")
    # submissions' primaryDocument points at the XSLT-rendered HTML (e.g. "xslFormDX08/primary_doc.xml").
    # The raw structured XML is the same filename WITHOUT that styling-dir prefix.
    raw = doc.split("/")[-1] or "primary_doc.xml"
    return sec_fetch(f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{nodash}/{raw}")


def _local(tag):  # strip XML namespace
    return tag.split("}")[-1]


def parse_related_persons(xml: str):
    """Extract [{name, relationships[]}] from a Form D primary_doc.xml (namespace-agnostic)."""
    root = ET.fromstring(xml.encode("utf-8"))
    people = []
    for node in root.iter():
        if _local(node.tag) != "relatedPersonInfo":
            continue
        first = last = ""
        rels = []
        for el in node.iter():
            ln = _local(el.tag)
            txt = (el.text or "").strip()
            if ln == "firstName":
                first = txt
            elif ln == "lastName":
                last = txt
            elif ln == "relationship" and txt:
                rels.append(txt)
        name = " ".join(p for p in (first, last) if p).strip()
        if name:
            people.append({"name": name, "relationships": rels})
    return people


def run_badactor(names):
    if not names:
        return {"feed_items": 0, "results": []}
    out = subprocess.run(
        ["python3", os.path.join(HERE, "badactor-watch.py"), "--names", "; ".join(names), "--json"],
        capture_output=True, text=True, env={**os.environ},
    )
    if out.returncode != 0:
        sys.exit(f"badactor-watch failed ({out.returncode}): {out.stderr.strip()}")
    return json.loads(out.stdout)


def main():
    ap = argparse.ArgumentParser(description="Screen a Reg D offering: Form D -> covered persons -> bad-actor monitor (never-opine).")
    ap.add_argument("--cik", required=True, help="issuer CIK (leading zeros optional)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    issuer, accession, doc = latest_form_d(args.cik)
    people = parse_related_persons(form_d_xml(args.cik, accession, doc))
    # Watchlist = the issuer entity + each named related person (the 506(d) covered persons).
    watchlist = [issuer] + [p["name"] for p in people]
    screen = run_badactor(watchlist)
    by_name = {r["watch_name"]: r for r in screen["results"]}

    if args.json:
        print(json.dumps({
            "issuer": issuer, "cik": str(int(args.cik)), "form_d_accession": accession,
            "covered_persons": people, "ap_feed_items": screen.get("feed_items"),
            "screen": screen["results"],
        }, indent=2))
        return

    flags = [r for r in screen["results"] if r["state"] == "escalate_to_counsel"]
    print(f"Offering screen | issuer: {issuer} | CIK {int(args.cik)} | Form D {accession}")
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
