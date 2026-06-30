#!/usr/bin/env python3
"""finra-portal-check.py - verify a Reg CF intermediary is a registered funding portal AND a
current FINRA member, from the two authoritative public registers. Never-opine.

THE OBLIGATION (17 CFR 227.400 + FINRA Funding Portal Rule 110): a crowdfunding intermediary
must register with the SEC as a funding portal (Form Funding Portal) AND become a member of a
national securities association (FINRA). Both are PUBLIC-REGISTER facts, so unlike most of the
funding-portal surface this leg is fully auto-verifiable - no private evidence, no legal judgment.

TWO LEGS, two authoritative sources, joined on the SEC file number (the stable unique key):
  1. SEC registration  -> EDGAR. A funding portal files Form Funding Portal as form type
     `CFPORTAL` (initial) / `CFPORTAL/A` (amendment) / `CFPORTAL-W` (withdrawal). Registered =
     a CFPORTAL exists and the latest CFPORTAL-family filing is NOT a withdrawal. Fetched via
     scripts/sec-fetch.sh (compliant User-Agent), reusing edgar_formd.fetch_submissions.
  2. FINRA membership  -> FINRA's "Funding Portals We Regulate" page. Its own words: "The
     following crowdfunding intermediaries are registered with the SEC as funding portals and
     are funding portal members of FINRA." Presence on the list == FINRA member. Matched on the
     SEC file number (Form C's `007-00042` normalizes to FINRA's `7-42`).

DISCIPLINE: resolves to satisfied / escalate_to_counsel / open(unverified) - never "compliant".
`satisfied` requires BOTH registers to confirm on the file-number key with reconciling legal
names (a pure public-register fact, like the Form D exemption-claimed leg). Any register
inconsistency, withdrawal, or unreachable source routes to escalate/open. Counsel still owns it.

USAGE
  export SEC_CONTACT_EMAIL="you@example.com"
  python3 scripts/finra-portal-check.py --cik 1666102 --file-number 007-00042
  python3 scripts/finra-portal-check.py --cik 1666102 --file-number 007-00042 --json
"""
import argparse
import json
import os
import re
import subprocess
import sys

import edgar_formd as efd

HERE = os.path.dirname(os.path.abspath(__file__))
FINRA_FP_URL = "https://www.finra.org/about/firms-we-regulate/funding-portals-we-regulate"

# CFPORTAL family on EDGAR. A "-W" suffix is a withdrawal of the funding-portal registration.
CFPORTAL_INITIAL = "CFPORTAL"
def _is_cfportal(form: str) -> bool:
    return form.upper().startswith("CFPORTAL")
def _is_withdrawal(form: str) -> bool:
    return "CFPORTAL-W" in form.upper()


def normalize_file_number(fn: str) -> str:
    """SEC funding-portal file number -> FINRA's display form. '007-00042' -> '7-42'.
    Strips the leading-zero padding on each hyphen-separated part (FINRA drops it)."""
    if not fn:
        return ""
    parts = [p.lstrip("0") or "0" for p in str(fn).strip().split("-")]
    return "-".join(parts)


def _strip_tags(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip()


def _fmt_cik(cik) -> str:
    """CIK as an int-normalized string for display; degrade to the raw value if non-numeric."""
    try:
        return str(int(cik))
    except (TypeError, ValueError):
        return str(cik)


# ---- Leg 1: SEC funding-portal registration (EDGAR, authoritative + deterministic) ----------

def check_sec_registration(cik: str) -> dict:
    """Inspect the intermediary CIK's EDGAR filing history for the CFPORTAL family."""
    try:
        subs = efd.fetch_submissions(cik)
    except SystemExit as e:
        return {"accessible": False, "error": str(e)}
    legal_name = subs.get("name")
    r = subs.get("filings", {}).get("recent", {})
    forms = list(zip(r.get("form", []), r.get("filingDate", []), r.get("accessionNumber", [])))
    cfp = [(f, d, a) for f, d, a in forms if _is_cfportal(f)]  # recent-first order
    has_initial = any(f.upper().startswith(CFPORTAL_INITIAL) for f, _, _ in cfp)
    latest = cfp[0] if cfp else None
    if not cfp:
        status = "NOT_REGISTERED"
    elif latest and _is_withdrawal(latest[0]):
        status = "WITHDRAWN"
    else:
        status = "REGISTERED"
    return {
        "accessible": True,
        "legal_name": legal_name,
        "status": status,
        "cfportal_count": len(cfp),
        "latest_form": latest[0] if latest else None,
        "latest_date": latest[1] if latest else None,
        "earliest_date": cfp[-1][1] if cfp else None,
        "has_initial": has_initial,
    }


# ---- Leg 2: FINRA membership (the "Funding Portals We Regulate" list) -----------------------

def fetch_finra_list() -> str:
    """Fetch the FINRA funding-portals page as raw HTML (deterministic parse, not a model
    summary). FINRA is a public site; we send a descriptive User-Agent with contact info."""
    ua = f"claude-obsidian funding-portal-check ({os.environ.get('SEC_CONTACT_EMAIL', 'no-contact-set')})"
    out = subprocess.run(
        ["curl", "-sS", "-L", "--max-time", "30", "-A", ua, FINRA_FP_URL],
        capture_output=True, text=True)
    if out.returncode != 0 or not out.stdout.strip():
        raise RuntimeError(f"FINRA fetch failed (rc={out.returncode}): {out.stderr.strip()[:200]}")
    return out.stdout


def parse_finra_entry(html: str, file_number: str) -> dict:
    """Find the funding-portal entry whose SEC file number matches `file_number` (normalized),
    by the `filenum=<n>` query in its EDGAR link (the exact, stable key).

    Robust against malformed markup: split the page into one chunk per portal at each
    `multicolumn-container` div (so a missing </p> can't bleed two entries together), bound each
    chunk at the next container/hr, and tolerate class-attribute variants + escaped/raw `&`."""
    fnorm = normalize_file_number(file_number)
    # One chunk per portal; chunks[0] is the page preamble before the first entry.
    for chunk in re.split(r'<div\b[^>]*class="multicolumn-container', html)[1:]:
        # Bound to THIS entry only (defensive: stop before the next container/hr if one leaked in).
        entry = re.split(r'<hr\b|<div\b', chunk)[0]
        m = re.search(r'filenum=([0-9-]+)[&"\']', entry)
        if m and m.group(1) == fnorm:
            name = re.search(r"<strong>(.*?)</strong>", entry, re.S)
            other = re.search(r"Other Name\(s\):\s*(.*?)(?:<br|$)", entry, re.S)
            site = re.search(r"Website URL\(s\):\s*(.*?)(?:<br|$)", entry, re.S)
            secfn = re.search(r"SEC File No\.?:\s*([0-9-]+)", entry)
            return {
                "found": True,
                "legal_name": _strip_tags(name.group(1)) if name else None,
                "other_names": _strip_tags(other.group(1)) if other else None,
                "website": _strip_tags(site.group(1)) if site else None,
                "finra_file_number": secfn.group(1) if secfn else fnorm,
            }
    return {"found": False, "normalized_file_number": fnorm}


def check_finra_membership(file_number: str) -> dict:
    try:
        html = fetch_finra_list()
    except (RuntimeError, FileNotFoundError, OSError) as e:
        # A missing/broken fetch tool (e.g. curl absent) is a "register unreachable" condition,
        # not a crash - the never-opine design routes it to `open`, never a silent clearance.
        return {"accessible": False, "error": str(e)}
    entry = parse_finra_entry(html, file_number)
    entry["accessible"] = True
    return entry


# ---- Combine: never-opine verdict -----------------------------------------------------------

# Legal-entity-type suffixes dropped before comparing names (so "Ksdaq Inc." == "Ksdaq").
_CORP_SUFFIXES = {"inc", "incorporated", "llc", "lllp", "pllc", "corp", "corporation", "ltd",
                  "limited", "co", "company", "lp", "llp", "plc", "pc"}


def _name_tokens(s: str) -> set:
    return {t for t in re.findall(r"[a-z0-9]+", (s or "").lower()) if t not in _CORP_SUFFIXES}


def _names_reconcile(a: str, b: str) -> bool:
    """Token-set equality after stripping punctuation + corporate-type suffixes - NOT substring
    containment (which would let a mis-parsed generic token like 'Capital' reconcile against
    'Republic Capital LLC' and suppress a legitimate escalation). The SEC file number is the
    authoritative join key; this is a secondary sanity gate, so a strict rule that errs toward
    escalation (counsel disambiguates) is the safe never-opine bias - it never causes a false
    clearance, only a safe extra flag."""
    ta, tb = _name_tokens(a), _name_tokens(b)
    if not ta or not tb:
        return False
    return ta == tb


def verify_portal(cik=None, file_number=None, crd=None, name=None) -> dict:
    sec = check_sec_registration(cik) if cik else {"accessible": False, "error": "no CIK provided"}
    finra = check_finra_membership(file_number) if file_number else {"accessible": False, "error": "no file number provided"}

    evidence, name_flag = [], None
    if sec.get("accessible"):
        evidence.append(f"EDGAR: CIK {_fmt_cik(cik)} legal name '{sec.get('legal_name')}', "
                        f"CFPORTAL status {sec.get('status')} "
                        f"(latest {sec.get('latest_form')} {sec.get('latest_date')}, {sec.get('cfportal_count')} filing(s))")
    if finra.get("accessible") and finra.get("found"):
        evidence.append(f"FINRA list: '{finra.get('legal_name')}' (other names: {finra.get('other_names')}), "
                        f"SEC File No. {finra.get('finra_file_number')}, {finra.get('website')}")

    # Source reachability first - never silently pass on an unreachable register.
    if not sec.get("accessible") or not finra.get("accessible"):
        unreachable = []
        if not sec.get("accessible"):
            unreachable.append(f"EDGAR ({sec.get('error')})")
        if not finra.get("accessible"):
            unreachable.append(f"FINRA ({finra.get('error')})")
        return {"state": "open", "evidence": evidence,
                "note": f"Could not reach an authoritative register: {', '.join(unreachable)}. "
                        "Re-run when reachable; do not treat as a clearance.",
                "sec": sec, "finra": finra}

    if sec["status"] == "WITHDRAWN":
        return {"state": "escalate_to_counsel", "evidence": evidence,
                "note": f"The funding-portal registration was WITHDRAWN on EDGAR "
                        f"({sec.get('latest_form')} {sec.get('latest_date')}) - the intermediary is NOT a "
                        "currently registered portal. Exemption-fatal; counsel assesses.",
                "sec": sec, "finra": finra}
    if sec["status"] == "NOT_REGISTERED":
        return {"state": "escalate_to_counsel", "evidence": evidence,
                "note": f"No CFPORTAL (Form Funding Portal) registration found on EDGAR for CIK {_fmt_cik(cik)} - "
                        "the named intermediary does not appear to be an SEC-registered funding portal. Counsel assesses.",
                "sec": sec, "finra": finra}

    # SEC says REGISTERED from here.
    if not finra.get("found"):
        return {"state": "escalate_to_counsel", "evidence": evidence,
                "note": f"SEC-registered as a funding portal (CFPORTAL) but file number "
                        f"{normalize_file_number(file_number)} is NOT on FINRA's current funding-portal list - "
                        "registers are inconsistent. Disambiguate (name change / withdrawal lag); counsel assesses.",
                "sec": sec, "finra": finra}

    # Both registers confirm on the file-number key. Reconcile legal names.
    if not _names_reconcile(sec.get("legal_name"), finra.get("legal_name")):
        name_flag = (f"EDGAR legal name '{sec.get('legal_name')}' and FINRA legal name "
                     f"'{finra.get('legal_name')}' do not reconcile on file number "
                     f"{normalize_file_number(file_number)} - disambiguate before relying.")
        return {"state": "escalate_to_counsel", "evidence": evidence, "note": name_flag,
                "sec": sec, "finra": finra}

    # Pure public-register fact, both legs confirmed, names reconcile.
    note = (f"Both authoritative registers confirm on SEC file number {normalize_file_number(file_number)}: "
            f"SEC-registered funding portal (CFPORTAL active since {sec.get('earliest_date')}) AND a current "
            f"FINRA member (on FINRA's funding-portal list). Legal entity '{sec.get('legal_name')}'"
            + (f", trading as '{finra.get('other_names')}'." if finra.get("other_names") else "."))
    if name and finra.get("other_names") and not _names_reconcile(name, finra.get("legal_name")) \
            and not _names_reconcile(name, finra.get("other_names")):
        note += (f" NOTE: the Form C names the intermediary '{name}', which differs from both the legal "
                 "name and the listed other-name - confirm it is the same entity.")
    return {"state": "satisfied", "evidence": evidence, "note": note, "sec": sec, "finra": finra}


def main():
    ap = argparse.ArgumentParser(description="Verify a Reg CF intermediary is a registered funding portal + FINRA member (never-opine).")
    ap.add_argument("--cik", help="intermediary CIK (from Form C commissionCik)")
    ap.add_argument("--file-number", help="SEC file number, e.g. 007-00042 (from Form C commissionFileNumber)")
    ap.add_argument("--crd", help="intermediary CRD (context only)")
    ap.add_argument("--name", help="intermediary name as shown on the Form C (for disambiguation)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if not args.cik and not args.file_number:
        ap.error("provide at least --cik and/or --file-number")

    result = verify_portal(args.cik, args.file_number, args.crd, args.name)
    if args.json:
        print(json.dumps(result, indent=2))
        return
    MARK = {"satisfied": "OK ", "escalate_to_counsel": "FLAG->counsel", "open": "open"}
    print(f"[{MARK.get(result['state'], result['state'])}] portal_finra_member  (file {args.file_number}, CIK {args.cik}, CRD {args.crd})")
    for ev in result["evidence"]:
        print(f"  - {ev}")
    print(f"  -> {result['note']}")
    print("\nThis check assembles from public registers and flags. It never concludes. Counsel opines.")


if __name__ == "__main__":
    main()
