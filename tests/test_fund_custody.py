#!/usr/bin/env python3
"""test_fund_custody.py — hermetic tests for scripts/fund-custody-check.py (money-transmission leg).

Covers parsing the portal's Form Funding Portal (CFPORTAL) custody disclosures from a canned XML,
the latest-CFPORTAL selection, the entity-name match, and every branch of verify_fund_custody's
never-opine verdict (BD-confirmed / third-party-unconfirmed / portal-holds-funds / no-custodian /
no-CFPORTAL / EDGAR-unreachable). No network: load_portal_custody + verify_custodian_is_bd are
monkeypatched. Pure stdlib.

Usage:
  python3 tests/test_fund_custody.py
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))  # so fund-custody-check can `import edgar_formd`

spec = importlib.util.spec_from_file_location("fund_custody_check", SCRIPTS / "fund-custody-check.py")
fcc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fcc)


class Fail(SystemExit):
    pass


def assert_eq(label, expected, actual):
    if expected != actual:
        raise Fail(f"FAIL {label}: expected {expected!r}, got {actual!r}")
    print(f"OK   {label}")


def assert_true(label, cond, hint=""):
    if not cond:
        raise Fail(f"FAIL {label}{(': ' + hint) if hint else ''}")
    print(f"OK   {label}")


# Canned Form Funding Portal (CFPORTAL) — escrowArrangements wraps the structured
# investorFundsContacts (name + address) and compensationDesc, mirroring the real schema.
CFPORTAL_XML = """<?xml version="1.0" encoding="UTF-8"?>
<edgarSubmission xmlns="http://www.sec.gov/edgar/crowdfunding" xmlns:com="http://www.sec.gov/edgar/common">
  <formData>
    <identifyingInformation><nameOfPortal>Ksdaq Inc.</nameOfPortal></identifyingInformation>
    <escrowArrangements>
      <investorFundsContacts>
        <investorFundsContactName>North Capital Private Securities Corporation</investorFundsContactName>
        <investorFundsAddress>
          <com:street1>623 E Fort Union Blvd, Suite 101</com:street1>
          <com:city>Midval</com:city><com:stateOrCountry>UT</com:stateOrCountry><com:zipCode>84047</com:zipCode>
        </investorFundsAddress>
        <investorFundsContactPhone>415-315-9916</investorFundsContactPhone>
      </investorFundsContacts>
      <compensationDesc>Mr. Crowd charges issuers a fee equal to a percentage of gross proceeds.</compensationDesc>
    </escrowArrangements>
  </formData>
</edgarSubmission>"""

NEVER_OPINE = {"satisfied", "open", "escalate_to_counsel", "n/a", "satisfied_by_counsel"}


def _custody(custodian="North Capital Private Securities Corporation", portal="Ksdaq Inc.", has_cfportal=True):
    return {"accessible": True, "has_cfportal": has_cfportal, "portal_legal_name": portal,
            "portal_name": portal, "custodian_name": custodian, "custodian_location": "Midval, UT",
            "cfportal_form": "CFPORTAL/A", "cfportal_date": "2025-10-29", "cfportal_accession": "x"}


def _patch(custody, bd):
    fcc.load_portal_custody = lambda cik: custody
    fcc.verify_custodian_is_bd = lambda name: bd


# ─── parse_cfportal ──────────────────────────────────────────────────────────
def test_parse_cfportal():
    d = fcc.parse_cfportal(CFPORTAL_XML)
    assert_eq("portal name", "Ksdaq Inc.", d["portal_name"])
    assert_eq("custodian (investorFundsContactName)", "North Capital Private Securities Corporation", d["custodian_name"])
    assert_eq("custodian location (scoped to the funds block)", "Midval, UT", d["custodian_location"])
    assert_true("compensation captured", d["compensation_desc"].startswith("Mr. Crowd charges"))


# ─── _latest_cfportal: take the MOST-RECENT CFPORTAL, INCLUDING a withdrawal ──
def test_latest_cfportal_returns_most_recent_including_withdrawal():
    subs = {"filings": {"recent": {
        "form": ["CFPORTAL-W", "CFPORTAL/A", "CFPORTAL"],
        "filingDate": ["2026-01-01", "2025-10-29", "2016-04-15"],
        "accessionNumber": ["acc-w", "acc-a", "acc-init"]}}}
    picked = fcc._latest_cfportal(subs)
    # MUST return the withdrawal (latest) so the caller can escalate - NOT skip to the prior live
    # filing (that would falsely reassure on a deregistered portal).
    assert_eq("latest filing is the withdrawal", "acc-w", picked[0])
    assert_eq("and it is reported as the -W form", "CFPORTAL-W", picked[1])


def test_latest_cfportal_live_when_no_withdrawal():
    subs = {"filings": {"recent": {
        "form": ["CFPORTAL/A", "CFPORTAL"], "filingDate": ["2025-10-29", "2016-04-15"],
        "accessionNumber": ["acc-a", "acc-init"]}}}
    assert_eq("no withdrawal → latest live CFPORTAL/A", "acc-a", fcc._latest_cfportal(subs)[0])


# ─── disclosure-answer scan: precise scoping (negative-event subtrees only) ───
_DISCLOSURES_CLEAN = ("<disclosureAnswers>"
                      "<criminalDisclosure><isConvictedOfFelony>N</isConvictedOfFelony></criminalDisclosure>"
                      "<regulatoryActionDisclosure><isOrderAgainst>N</isOrderAgainst>"
                      "<isAuthorizedToActAttorney>Y</isAuthorizedToActAttorney></regulatoryActionDisclosure>"
                      "<financialDisclosure><hasSubjectOfBankruptcy>N</hasSubjectOfBankruptcy></financialDisclosure>"
                      "</disclosureAnswers>")


def _cfportal_with(disclosures, extra=""):
    return CFPORTAL_XML.replace("</formData>", disclosures + extra + "</formData>")


def test_parse_disclosures_clean_ignores_neutral_fields():
    # All negative events; a neutral structural Y (isEngagedInNonSecurities, outside the subtrees) and
    # the neutral isAuthorizedToActAttorney=Y (inside, denylisted) must NOT be reported as events.
    d = fcc.parse_cfportal(_cfportal_with(_DISCLOSURES_CLEAN, "<isEngagedInNonSecurities>Y</isEngagedInNonSecurities>"))
    assert_eq("clean disclosures → no affirmative events", [], d["affirmative_disclosures"])


def test_parse_disclosures_flags_real_event_only():
    d = fcc.parse_cfportal(_cfportal_with(_DISCLOSURES_CLEAN.replace("<isOrderAgainst>N", "<isOrderAgainst>Y")))
    assert_true("real regulatory event flagged", "isOrderAgainst" in d["affirmative_disclosures"])
    assert_true("neutral isAuthorizedToActAttorney NOT flagged", "isAuthorizedToActAttorney" not in d["affirmative_disclosures"])


def test_parse_disclosures_flags_has_prefixed_event():
    d = fcc.parse_cfportal(_cfportal_with(_DISCLOSURES_CLEAN.replace("<hasSubjectOfBankruptcy>N", "<hasSubjectOfBankruptcy>Y")))
    assert_true("has-prefixed financial event flagged", "hasSubjectOfBankruptcy" in d["affirmative_disclosures"])


def test_parse_disclosures_prefix_agnostic():
    # A negative-event leaf that does NOT use an is/has/does prefix must still be caught - relying on
    # the naming convention would silently miss it (a false 'all-negative' clearance).
    dz = _DISCLOSURES_CLEAN.replace("</regulatoryActionDisclosure>", "<orderType>Y</orderType></regulatoryActionDisclosure>")
    d = fcc.parse_cfportal(_cfportal_with(dz))
    assert_true("non-conventional field name still flagged", "orderType" in d["affirmative_disclosures"])


def test_parse_disclosure_subtrees_seen():
    d = fcc.parse_cfportal(_cfportal_with(_DISCLOSURES_CLEAN))
    assert_true("subtree count exposed (>=3 in the fixture)", d["disclosure_subtrees_seen"] >= 3)


def test_latest_cfportal_none_when_absent():
    subs = {"filings": {"recent": {"form": ["C", "D"], "filingDate": ["x", "y"], "accessionNumber": ["1", "2"]}}}
    assert_true("no CFPORTAL → None", fcc._latest_cfportal(subs) is None)


# ─── _same_entity: name is the join key here (superset tolerated) ────────────
def test_same_entity():
    assert_true("exact (case-insensitive)", fcc._same_entity("North Capital Private Securities Corporation",
                                                             "NORTH CAPITAL PRIVATE SECURITIES CORPORATION"))
    assert_true("EDGAR superset of custodian tokens",
                fcc._same_entity("North Capital Private Securities", "North Capital Private Securities Corporation"))
    assert_true("different entity rejected", not fcc._same_entity("North Capital", "Republic Crowdfunding LLC"))


# ─── verify_fund_custody branches ────────────────────────────────────────────
def test_custody_bd_confirmed_open_with_strong_evidence():
    _patch(_custody(), {"checked": True, "is_registered_bd": True, "cik": "1496269",
                        "edgar_name": "NORTH CAPITAL PRIVATE SECURITIES CORPORATION", "evidence": "files X-17A-5 (FOCUS) on EDGAR"})
    r = fcc.verify_fund_custody("1666102")
    assert_eq("qualified third-party BD → open (not satisfied; AML private)", "open", r["state"])
    assert_true("evidence names the registered BD", any("registered broker-dealer" in e for e in r["evidence"]))
    assert_true("note keeps AML/escrow private", "private" in r["note"])


def test_custody_third_party_bd_unconfirmed_still_open():
    _patch(_custody(custodian="Some Escrow Bank, N.A."),
           {"checked": True, "is_registered_bd": False, "reason": "no X-17A-5 filer matched"})
    r = fcc.verify_fund_custody("1666102")
    assert_eq("third party named but BD unconfirmed → open", "open", r["state"])
    assert_true("note suggests it may be a bank", "bank" in r["note"])


def test_custody_portal_holds_funds_escalates():
    _patch(_custody(custodian="Ksdaq Inc."), {"checked": False})  # custodian == portal
    r = fcc.verify_fund_custody("1666102")
    assert_eq("portal names itself as funds custodian → escalate", "escalate_to_counsel", r["state"])
    assert_true("note flags money-transmitter exposure", "money-transmitter" in r["note"])


def test_custody_overlapping_name_not_self_dealing():
    # A distinct custodian whose name merely OVERLAPS the portal's must NOT trip the
    # "portal holds its own funds" escalation (exact-equality, not subset, guards that branch).
    _patch(_custody(portal="Republic", custodian="Republic Capital LLC"),
           {"checked": True, "is_registered_bd": False, "reason": "unconfirmed"})
    r = fcc.verify_fund_custody("1666102")
    assert_eq("overlapping-but-distinct custodian → open, not self-dealing escalate", "open", r["state"])


def test_custody_no_custodian_escalates():
    _patch(_custody(custodian=None), {"checked": False})
    r = fcc.verify_fund_custody("1666102")
    assert_eq("no disclosed custodian → escalate", "escalate_to_counsel", r["state"])


def test_custody_no_cfportal_is_open():
    _patch(_custody(has_cfportal=False), {"checked": False})
    r = fcc.verify_fund_custody("1666102")
    assert_eq("no CFPORTAL on file → open (unverified)", "open", r["state"])


def test_custody_withdrawn_portal_escalates():
    # Latest CFPORTAL filing is a withdrawal -> the portal is deregistered; must escalate, never
    # read a prior filing's stale escrow as if it were live.
    withdrawn = {"accessible": True, "has_cfportal": True, "withdrawn": True,
                 "portal_legal_name": "Ksdaq Inc.", "cfportal_form": "CFPORTAL-W", "cfportal_date": "2026-01-01"}
    _patch(withdrawn, {"checked": False})
    r = fcc.verify_fund_custody("1666102")
    assert_eq("withdrawn registration → escalate", "escalate_to_counsel", r["state"])
    assert_true("note says WITHDRAWN", "WITHDRAWN" in r["note"])


def test_custody_edgar_unreachable_is_open():
    def _boom(cik):
        raise SystemExit("fetch failed")
    fcc.load_portal_custody = _boom
    r = fcc.verify_fund_custody("1666102")
    assert_eq("EDGAR unreachable → open (not a clearance)", "open", r["state"])
    assert_true("note says do not treat as a clearance", "clearance" in r["note"].lower())


def test_all_custody_branches_never_opine():
    cases = [
        (_custody(), {"checked": True, "is_registered_bd": True, "cik": "1", "edgar_name": "X", "evidence": "x"}),
        (_custody(custodian="Bank N.A."), {"checked": True, "is_registered_bd": False, "reason": "r"}),
        (_custody(custodian="Ksdaq Inc."), {"checked": False}),
        (_custody(custodian=None), {"checked": False}),
        (_custody(has_cfportal=False), {"checked": False}),
    ]
    for i, (cust, bd) in enumerate(cases):
        _patch(cust, bd)
        r = fcc.verify_fund_custody("1666102")
        assert_true(f"case {i} → never-opine state", r["state"] in NEVER_OPINE, f"got {r['state']!r}")


def main():
    test_parse_cfportal()
    test_parse_disclosures_clean_ignores_neutral_fields()
    test_parse_disclosures_flags_real_event_only()
    test_parse_disclosures_flags_has_prefixed_event()
    test_parse_disclosures_prefix_agnostic()
    test_parse_disclosure_subtrees_seen()
    test_latest_cfportal_returns_most_recent_including_withdrawal()
    test_latest_cfportal_live_when_no_withdrawal()
    test_latest_cfportal_none_when_absent()
    test_same_entity()
    test_custody_bd_confirmed_open_with_strong_evidence()
    test_custody_third_party_bd_unconfirmed_still_open()
    test_custody_portal_holds_funds_escalates()
    test_custody_overlapping_name_not_self_dealing()
    test_custody_no_custodian_escalates()
    test_custody_no_cfportal_is_open()
    test_custody_withdrawn_portal_escalates()
    test_custody_edgar_unreachable_is_open()
    test_all_custody_branches_never_opine()
    print("\nAll fund-custody tests passed.")


if __name__ == "__main__":
    main()
