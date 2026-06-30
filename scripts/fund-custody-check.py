#!/usr/bin/env python3
"""fund-custody-check.py - the money-transmission leg for a Reg CF funding portal. Never-opine.

THE OBLIGATION (17 CFR 227.303(e) + the money-transmission sovereign): a funding portal that is
NOT a broker-dealer must direct investors to transmit funds to a "qualified third party" - a
registered broker-dealer or a bank that has agreed in writing to hold the funds in escrow - and
the portal itself may NOT hold or handle investor funds (227.300(c)(2)). This is the structural
reason a compliant Reg CF raise has no state money-transmitter / FinCEN MSB exposure: the funds
sit with a BD or bank, both of which are carved out of MTL/MSB regimes.

WHAT IS PUBLIC (and now auto-verified end to end):
  1. The portal's own Form Funding Portal (EDGAR `CFPORTAL`) discloses, in structured fields, the
     entity that holds investor funds: `investorFundsContacts/investorFundsContactName` (+ address)
     inside `escrowArrangements`. So we can read WHO the funds go to - and confirm it is a third
     party DISTINCT from the portal (if the portal names itself -> money-transmission red flag).
  2. The named custodian's status as a "qualified third party" is itself public: a registered
     broker-dealer files annual `X-17A-5` FOCUS reports on EDGAR (mandated by SEA Rule 17a-5).
     Resolve the custodian name -> CIK via EDGAR's atom company search, then confirm X-17A-5 in its
     filing history. (A bank custodian won't file X-17A-5 - absence is "confirm manually", not a
     failure, since a bank is equally a qualified third party.)

WHAT STAYS PRIVATE (crisply delineated, never claimed): the executed escrow/custody agreement for
THIS specific offering, the actual fund flows, and the AML/BSA program. So this leg resolves to
`open` (heavily evidenced) when the structure checks out - not `satisfied` - and to
`escalate_to_counsel` when the portal appears to handle funds itself.

USAGE
  export SEC_CONTACT_EMAIL="you@example.com"
  python3 scripts/fund-custody-check.py --portal-cik 1666102
  python3 scripts/fund-custody-check.py --portal-cik 1666102 --json
"""
import argparse
import json
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET

import edgar_formd as efd


# ---- Parse the portal's Form Funding Portal (CFPORTAL) -------------------------------------

def _latest_cfportal(subs: dict):
    """MOST-RECENT CFPORTAL-family filing (recent-first), INCLUDING withdrawals -> (accession,
    form, date) or None. The caller must check for a `-W`: if the latest filing is a withdrawal,
    the portal is deregistered and reading a prior live CFPORTAL's escrow would falsely reassure
    on a portal that no longer exists (mirrors finra-portal-check.check_sec_registration)."""
    r = subs.get("filings", {}).get("recent", {})
    for form, date, acc in zip(r.get("form", []), r.get("filingDate", []), r.get("accessionNumber", [])):
        if form.upper().startswith("CFPORTAL"):
            return acc, form, date
    return None


# The four negative-event disclosure subtrees in a Form Funding Portal. We scan ONLY these (so the
# neutral structural booleans elsewhere - isSucceedingBusiness, isEngagedInNonSecurities - are never
# mistaken for an event). isAuthorizedToActAttorney sits inside regulatoryActionDisclosure but is a
# non-negative-event question, so it is explicitly excluded.
_DISCLOSURE_SUBTREES = {"criminalDisclosure", "regulatoryActionDisclosure",
                        "civilJudicialActionDisclosure", "financialDisclosure"}
_NEUTRAL_DISCLOSURE_FIELDS = {"isAuthorizedToActAttorney"}
_AFFIRMATIVE = {"Y", "YES", "TRUE"}


def _scan_disclosures(root) -> list:
    """Affirmative (Y/true) answers within the criminal/regulatory/civil/financial disclosure
    subtrees - the portal's self-disclosed events (FINRA FP Rule 200 standing). Empty == clean."""
    out = []
    for el in root.iter():
        if efd._ln(el.tag) not in _DISCLOSURE_SUBTREES:
            continue
        for sub in el.iter():
            n = efd._ln(sub.tag)
            if n.startswith(("is", "has", "does")) and n not in _NEUTRAL_DISCLOSURE_FIELDS \
                    and (sub.text or "").strip().upper() in _AFFIRMATIVE and n not in out:
                out.append(n)
    return out


def parse_cfportal(xml: str) -> dict:
    """Extract the fund-custody + conduct disclosures from a Form Funding Portal (namespace-agnostic)."""
    root = ET.fromstring(xml.encode("utf-8"))
    # Single-custodian assumption: we read the FIRST investorFundsContacts block. A portal disclosing
    # multiple investor-funds custodians (rare) would have the rest dropped; the named one is still a
    # qualified third party, so the verdict direction is unaffected, but note the limitation.
    funds = efd._find(root, "investorFundsContacts")
    custodian = efd._first_text(funds, "investorFundsContactName") if funds is not None else None
    loc = None
    if funds is not None:
        city = efd._first_text(funds, "city")
        state = efd._first_text(funds, "stateOrCountry")
        loc = ", ".join(p for p in (city, state) if p) or None
    return {
        "portal_name": efd._first_text(root, "nameOfPortal"),
        "custodian_name": custodian,
        "custodian_location": loc,
        "compensation_desc": efd._first_text(root, "compensationDesc"),
        "affirmative_disclosures": _scan_disclosures(root),
    }


def load_portal_custody(portal_cik: str) -> dict:
    subs = efd.fetch_submissions(portal_cik)
    picked = _latest_cfportal(subs)
    if not picked:
        return {"accessible": True, "has_cfportal": False, "portal_legal_name": subs.get("name")}
    acc, form, date = picked
    if "CFPORTAL-W" in form.upper():
        # Latest filing is a withdrawal -> the portal is deregistered; do NOT read a prior filing's
        # stale escrow data. The caller routes this to escalate.
        return {"accessible": True, "has_cfportal": True, "withdrawn": True,
                "portal_legal_name": subs.get("name"), "cfportal_form": form, "cfportal_date": date}
    data = parse_cfportal(efd.fetch_archive_doc(portal_cik, acc, "primary_doc.xml"))
    data.update({"accessible": True, "has_cfportal": True, "withdrawn": False,
                 "portal_legal_name": subs.get("name"),
                 "cfportal_accession": acc, "cfportal_form": form, "cfportal_date": date})
    return data


# ---- Confirm the custodian is a qualified third party (registered broker-dealer) -----------

_CORP_SUFFIXES = {"inc", "incorporated", "llc", "lllp", "pllc", "corp", "corporation", "ltd",
                  "limited", "co", "company", "lp", "llp", "plc", "pc"}


def _tokens(s: str) -> set:
    return {t for t in re.findall(r"[a-z0-9]+", (s or "").lower()) if t not in _CORP_SUFFIXES}


def _same_entity(a: str, b: str) -> bool:
    """Custodian name (CFPORTAL) vs an EDGAR conformed-name, for the BD name-match: here the NAME
    is the join key (no file number) and EDGAR conformed-names are often a SUPERSET (e.g. add
    'CORPORATION'), so subset tolerance is desired. Both empty -> False. NOT used for the
    portal-self-dealing test (that needs exact equality - see _exact_entity)."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return False
    return ta == tb or ta <= tb or tb <= ta


def _exact_entity(a: str, b: str) -> bool:
    """Strict token-set equality. Used for the portal-self-dealing check so a custodian whose name
    merely OVERLAPS the portal's (e.g. a distinct 'Republic Capital LLC' vs a 'Republic' portal)
    is not falsely flagged as 'the portal holds its own funds' - that escalation must fire only
    when the disclosed custodian truly IS the portal."""
    ta, tb = _tokens(a), _tokens(b)
    return bool(ta) and ta == tb


def verify_custodian_is_bd(name: str) -> dict:
    """Resolve the custodian name to an EDGAR entity that files X-17A-5 (a registered BD)."""
    if not name:
        return {"checked": False, "reason": "no custodian named"}
    q = urllib.parse.quote_plus(name)
    url = (f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company={q}"
           f"&type=X-17A-5&output=atom&count=10")
    try:
        atom = efd.sec_fetch(url)
    except SystemExit as e:
        return {"checked": False, "reason": f"EDGAR atom search unreachable: {e}"}
    # Scope both fields to the same <company-info> block so a multi-result atom can't pair a CIK
    # from one entity with a conformed-name from another (the _same_entity gate then guards a
    # non-reconciling match; direction is safe -> falls to "unconfirmed" -> open, never a clearance).
    ci = re.search(r"<company-info>(.*?)</company-info>", atom, re.S | re.I)
    scope = ci.group(1) if ci else atom
    cik = re.search(r"<cik>(\d+)</cik>", scope, re.I)
    conformed = re.search(r"<conformed-name>(.*?)</conformed-name>", scope, re.I | re.S)
    if not cik or not conformed:
        return {"checked": True, "is_registered_bd": False,
                "reason": "no X-17A-5 filer matched the custodian name in EDGAR"}
    cname = conformed.group(1).strip()
    if not _same_entity(name, cname):
        return {"checked": True, "is_registered_bd": False, "candidate_cik": cik.group(1),
                "candidate_name": cname, "reason": "closest X-17A-5 filer name does not reconcile"}
    # Confirm X-17A-5 actually appears in that CIK's filing history (deterministic).
    try:
        subs = efd.fetch_submissions(cik.group(1))
    except SystemExit as e:
        return {"checked": False, "reason": f"submissions unreachable: {e}"}
    has_x17 = "X-17A-5" in subs.get("filings", {}).get("recent", {}).get("form", [])
    return {"checked": True, "is_registered_bd": has_x17, "cik": cik.group(1),
            "edgar_name": subs.get("name"), "evidence": "files X-17A-5 (FOCUS) on EDGAR" if has_x17 else "no X-17A-5 found"}


# ---- Combine: never-opine verdict ----------------------------------------------------------

def verify_fund_custody(portal_cik: str) -> dict:
    try:
        cust = load_portal_custody(portal_cik)
    except SystemExit as e:
        return {"state": "open", "evidence": [],
                "note": f"Could not reach EDGAR for the portal's Form Funding Portal ({e}). "
                        "Re-run; do not treat as a clearance.", "custody": None}

    if not cust.get("has_cfportal"):
        return {"state": "open", "evidence": [f"portal legal name: {cust.get('portal_legal_name')}"],
                "note": "No Form Funding Portal (CFPORTAL) on EDGAR for this intermediary CIK - cannot read the "
                        "disclosed fund-custody arrangement. Confirm the qualified third party + AML/BSA (private).",
                "custody": cust}

    if cust.get("withdrawn"):
        return {"state": "escalate_to_counsel",
                "evidence": [f"latest Form Funding Portal filing is a withdrawal "
                             f"({cust.get('cfportal_form')} {cust.get('cfportal_date')})"],
                "note": "The portal's funding-portal registration was WITHDRAWN (latest CFPORTAL filing is a "
                        "-W) - it is not a currently registered portal, so its prior fund-custody disclosure "
                        "cannot be relied on. Counsel assesses.",
                "custody": cust}

    portal = cust.get("portal_name") or cust.get("portal_legal_name")
    custodian = cust.get("custodian_name")
    evidence = [f"Form Funding Portal {cust.get('cfportal_form')} ({cust.get('cfportal_date')}): "
                f"investor-funds custodian disclosed as '{custodian}'"
                + (f" ({cust.get('custodian_location')})" if cust.get("custodian_location") else "")]

    if not custodian:
        return {"state": "escalate_to_counsel", "evidence": evidence,
                "note": "The portal's Form Funding Portal does not disclose a third-party investor-funds "
                        "custodian - confirm funds are NOT handled by the portal (227.300(c)(2)); a portal that "
                        "touches funds has state money-transmitter / FinCEN MSB exposure. Counsel assesses.",
                "custody": cust}

    if _exact_entity(portal, custodian):
        return {"state": "escalate_to_counsel", "evidence": evidence,
                "note": f"The disclosed investor-funds custodian ('{custodian}') appears to BE the portal itself - "
                        "a funding portal may not hold investor funds (227.300(c)(2)); this is direct "
                        "money-transmitter / MSB exposure. Counsel assesses.",
                "custody": cust}

    # A third party distinct from the portal is named -> the 227.303(e) structure is in place.
    bd = verify_custodian_is_bd(custodian)
    cust["custodian_bd_check"] = bd
    if bd.get("is_registered_bd"):
        evidence.append(f"custodian '{bd.get('edgar_name')}' (CIK {bd.get('cik')}) is a registered broker-dealer "
                        f"({bd.get('evidence')}) -> a qualified third party under 227.303(e)(1), MTL/MSB-exempt")
        note = ("Per the portal's Form Funding Portal, investor funds are directed to a QUALIFIED THIRD PARTY "
                f"(a registered broker-dealer) distinct from the portal - the 227.303(e) structure that keeps the "
                "raise out of state money-transmitter / FinCEN MSB scope. NOT a clearance: confirm the executed "
                "escrow/custody agreement for THIS offering and the portal's AML/BSA controls (private). Counsel confirms.")
    else:
        note = (f"Per the portal's Form Funding Portal, investor funds are directed to '{custodian}', a third party "
                "distinct from the portal. Could not auto-confirm it is a registered broker-dealer "
                f"({bd.get('reason', 'unconfirmed')}) - it may be a bank (equally a qualified third party) or a BD "
                "under a different registered name. Confirm qualified-third-party status + the executed escrow "
                "agreement + AML/BSA controls (private). Counsel confirms.")
    return {"state": "open", "evidence": evidence, "note": note, "custody": cust}


def main():
    ap = argparse.ArgumentParser(description="Verify the money-transmission / fund-custody leg of a Reg CF funding portal (never-opine).")
    ap.add_argument("--portal-cik", required=True, help="the intermediary CIK (from Form C commissionCik)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    result = verify_fund_custody(args.portal_cik)
    if args.json:
        print(json.dumps(result, indent=2))
        return
    # No "satisfied" entry: this check never returns satisfied by design (the executed escrow
    # agreement + AML/BSA are private); MARK.get falls back to the raw state if that ever changes.
    MARK = {"open": "open", "escalate_to_counsel": "FLAG->counsel"}
    print(f"[{MARK.get(result['state'], result['state'])}] funds_qualified_third_party  (portal CIK {args.portal_cik})")
    for ev in result["evidence"]:
        print(f"  - {ev}")
    print(f"  -> {result['note']}")
    print("\nThis check assembles from the portal's public SEC registration and flags. It never concludes. Counsel opines.")


if __name__ == "__main__":
    main()
