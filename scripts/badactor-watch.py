#!/usr/bin/env python3
"""badactor-watch.py - the first product atom (continuous bad-actor drift monitor).

WHAT IT IS
  One executable Control from docs/product-thesis.md: the Rule 506(d) bad-actor check,
  *continuous* leg. It polls the SEC's official Administrative Proceedings RSS feed and flags
  any watchlist name (an offering's officers / directors / 20%+ holders) that appears in a
  current proceeding.

THE DISCIPLINE (non-negotiable - see the thesis)
  This NEVER concludes that anyone is a "bad actor" or that an exemption is lost. A hit is an
  EVIDENCE ITEM that resolves to `escalate_to_counsel`: counsel disambiguates (same person?
  what was the order? does it fall within 506(d)'s covered events and look-back?) and opines.
  A non-hit is NOT a clearance - the RSS feed is a rolling window, not the full history.

DATA (verified 2026-06-29)
  GREEN: https://www.sec.gov/rss/litigation/admin.xml (live, structured, free).
  Historical lookup (SALI) is JS-rendered (no GET-JSON) -> a v2 concern (Playwright/archives).

USAGE
  export SEC_CONTACT_EMAIL="you@example.com"
  python3 scripts/badactor-watch.py --names "Jane Q Founder; Acme Holdings LLC"
  python3 scripts/badactor-watch.py --names-file watchlist.txt   # one name per line
  python3 scripts/badactor-watch.py --names "..." --json         # machine-readable output
"""
import argparse
import html
import json
import os
import re
import subprocess
import sys

ADMIN_RSS = "https://www.sec.gov/rss/litigation/admin.xml"


def fetch(url: str) -> str:
    """Fetch via scripts/sec-fetch.sh so we inherit the compliant User-Agent + redirects."""
    here = os.path.dirname(os.path.abspath(__file__))
    out = subprocess.run(
        ["bash", os.path.join(here, "sec-fetch.sh"), url],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        sys.exit(f"fetch failed ({out.returncode}): {out.stderr.strip()}")
    return out.stdout


def parse_items(xml: str):
    """Entity-tolerant RSS item parse (the feed carries unescaped chars that strict XML rejects)."""
    items = []
    for block in re.findall(r"<item>(.*?)</item>", xml, re.S):
        def field(tag):
            m = (re.search(rf"<{tag}>(.*?)</{tag}>", block, re.S)
                 or re.search(rf"<{tag}><!\[CDATA\[(.*?)\]\]></{tag}>", block, re.S))
            return html.unescape(re.sub(r"<[^>]+>", "", m.group(1)).strip()) if m else ""
        items.append({"title": field("title"), "date": field("pubDate"), "link": field("link")})
    return items


def load_names(args) -> list:
    names = []
    if args.names:
        names += [n.strip() for n in args.names.split(";") if n.strip()]
    if args.names_file:
        with open(args.names_file, encoding="utf-8") as fh:
            names += [ln.strip() for ln in fh if ln.strip()]
    return names


def check(names, items):
    """Substring match (case-insensitive). Deliberately broad: false positives are EXPECTED
    and are the point - every hit is for human disambiguation, never an auto-conclusion."""
    results = []
    for name in names:
        hits = [it for it in items if name.lower() in it["title"].lower()]
        if hits:
            results.append({
                "watch_name": name,
                "state": "escalate_to_counsel",
                "evidence": hits,
                "note": ("Name appears in a CURRENT SEC administrative proceeding. This is an "
                         "evidence item to DISAMBIGUATE and assess (same party? covered 506(d) "
                         "event? within look-back?) - NOT a disqualification determination. "
                         "Counsel opines."),
            })
        else:
            results.append({
                "watch_name": name,
                "state": "open",
                "evidence": [],
                "note": ("No match in the current AP feed window. NOT a clearance - this feed is "
                         "a rolling window; a full historical check needs SALI / archives."),
            })
    return results


def main():
    ap = argparse.ArgumentParser(description="Continuous Rule 506(d) bad-actor drift monitor (never-opine).")
    ap.add_argument("--names", help="semicolon-separated watchlist")
    ap.add_argument("--names-file", help="file with one name per line")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    args = ap.parse_args()

    names = load_names(args)
    if not names:
        ap.error("provide --names or --names-file")

    items = parse_items(fetch(ADMIN_RSS))
    results = check(names, items)

    if args.json:
        print(json.dumps({"feed": ADMIN_RSS, "feed_items": len(items), "results": results}, indent=2))
        return

    flagged = [r for r in results if r["state"] == "escalate_to_counsel"]
    print(f"Bad-actor drift monitor | source: {ADMIN_RSS} | {len(items)} current items")
    print(f"watchlist: {len(names)} | flagged for counsel: {len(flagged)} | conclusions drawn: 0\n")
    for r in results:
        mark = "FLAG -> counsel" if r["state"] == "escalate_to_counsel" else "open (no current match)"
        print(f"[{mark}] {r['watch_name']}")
        for ev in r["evidence"]:
            print(f"    - {ev['date'][:16]} | {ev['title'][:90]}")
        print(f"    {r['note']}\n")
    print("Reminder: this monitor assembles and flags. It never concludes. Counsel opines.")


if __name__ == "__main__":
    main()
