#!/usr/bin/env python3
"""test_finra_portal.py — hermetic tests for scripts/finra-portal-check.py.

Covers file-number normalization, deterministic parsing of the FINRA "Funding Portals We
Regulate" HTML (canned snippet mirroring the real structure), and the never-opine verdict
logic in verify_portal across every branch (satisfied / withdrawn / not-registered /
register-inconsistent / name-mismatch / source-unreachable). No network: the SEC + FINRA
fetches are monkeypatched. Pure stdlib.

Usage:
  python3 tests/test_finra_portal.py
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
import sys
sys.path.insert(0, str(SCRIPTS))  # so finra-portal-check can `import edgar_formd`

spec = importlib.util.spec_from_file_location("finra_portal_check", SCRIPTS / "finra-portal-check.py")
fp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fp)


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


# Canned FINRA list HTML — two entries in the real page's structure (div.multicolumn-container
# > p, EDGAR link carrying filenum=<n>&type=CFPORTAL, <strong>name</strong>, SEC File No.,
# Other Name(s), Website URL(s)).
FINRA_HTML = (
    '<div class="multicolumn-container"><p>'
    '<a href="http://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&filenum=7-8&type=CFPORTAL&owner=include&count=40">'
    '<strong>Jumpstart Micro, Inc</strong></a><br>SEC File No.: 7-8<br>Other Name(s): Issuance Express<br>'
    'Website URL(s): https://issuanceexpress.com/<br>9800 Wilshire Blvd<br>Beverly Hills, CA 90212</p></div>'
    '<hr class="dotted globalClearBoth">'
    '<div class="multicolumn-container"><p>'
    '<a href="http://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&filenum=7-42&type=CFPORTAL&owner=include&count=40">'
    '<strong>Ksdaq Inc.</strong></a><br>SEC File No.: 7-42<br>Other Name(s): Mr. Crowd<br>'
    'Website URL(s): https://www.MrCrowd.com<br>1302 Decca Industrial Centre<br>Hong Kong HKG</p></div>'
)

NEVER_OPINE = {"satisfied", "open", "escalate_to_counsel", "n/a", "satisfied_by_counsel"}


def _sec(status, name="Ksdaq Inc."):
    return {"accessible": True, "legal_name": name, "status": status, "cfportal_count": 25,
            "latest_form": "CFPORTAL/A" if status != "WITHDRAWN" else "CFPORTAL-W",
            "latest_date": "2025-10-29", "earliest_date": "2016-04-15", "has_initial": True}


def _patch(sec_result, html=FINRA_HTML):
    fp.check_sec_registration = lambda cik: sec_result
    fp.fetch_finra_list = lambda: html


# ─── normalize_file_number ───────────────────────────────────────────────────
def test_normalize_file_number():
    assert_eq("007-00042 → 7-42", "7-42", fp.normalize_file_number("007-00042"))
    assert_eq("007-00008 → 7-8", "7-8", fp.normalize_file_number("007-00008"))
    assert_eq("already-normalized 7-446 idempotent", "7-446", fp.normalize_file_number("7-446"))
    assert_eq("empty → empty", "", fp.normalize_file_number(""))
    assert_eq("all-zeros part keeps a 0", "7-0", fp.normalize_file_number("007-00000"))


# ─── parse_finra_entry: deterministic file-number match ──────────────────────
def test_parse_finra_entry_found():
    e = fp.parse_finra_entry(FINRA_HTML, "007-00042")
    assert_true("entry found by file number", e["found"])
    assert_eq("legal name", "Ksdaq Inc.", e["legal_name"])
    assert_eq("other names", "Mr. Crowd", e["other_names"])
    assert_eq("website", "https://www.MrCrowd.com", e["website"])
    assert_eq("finra file number", "7-42", e["finra_file_number"])


def test_parse_finra_entry_not_found():
    e = fp.parse_finra_entry(FINRA_HTML, "007-99999")
    assert_true("absent file number → not found", not e["found"])


def test_parse_finra_entry_does_not_collide():
    # 7-8 must not match the 7-42 block or vice versa.
    e = fp.parse_finra_entry(FINRA_HTML, "007-00008")
    assert_eq("7-8 resolves to Jumpstart, not Ksdaq", "Jumpstart Micro, Inc", e["legal_name"])


# ─── verify_portal branches ──────────────────────────────────────────────────
def test_verify_satisfied():
    _patch(_sec("REGISTERED"))
    r = fp.verify_portal(cik="1666102", file_number="007-00042", name="Mr. Crowd")
    assert_eq("both registers confirm → satisfied", "satisfied", r["state"])
    assert_true("note cites the file-number join", "7-42" in r["note"])


def test_verify_withdrawn_escalates():
    _patch(_sec("WITHDRAWN"))
    r = fp.verify_portal(cik="1666102", file_number="007-00042")
    assert_eq("withdrawn registration → escalate", "escalate_to_counsel", r["state"])
    assert_true("note says WITHDRAWN", "WITHDRAWN" in r["note"])


def test_verify_not_registered_escalates():
    _patch(_sec("NOT_REGISTERED"))
    r = fp.verify_portal(cik="2141182", file_number="007-00042")
    assert_eq("no CFPORTAL → escalate", "escalate_to_counsel", r["state"])


def test_verify_sec_registered_but_not_on_finra():
    _patch(_sec("REGISTERED"))
    r = fp.verify_portal(cik="1666102", file_number="007-99999")  # not in canned HTML
    assert_eq("SEC-registered but absent from FINRA list → escalate", "escalate_to_counsel", r["state"])
    assert_true("note flags register inconsistency", "inconsistent" in r["note"])


def test_verify_name_mismatch_escalates():
    _patch(_sec("REGISTERED", name="Totally Different LLC"))
    r = fp.verify_portal(cik="1666102", file_number="007-00042")
    assert_eq("file matches but legal names don't reconcile → escalate", "escalate_to_counsel", r["state"])


def test_verify_source_unreachable_is_open():
    fp.check_sec_registration = lambda cik: {"accessible": False, "error": "boom"}
    fp.fetch_finra_list = lambda: FINRA_HTML
    r = fp.verify_portal(cik="1666102", file_number="007-00042")
    assert_eq("unreachable register → open (not a clearance)", "open", r["state"])
    assert_true("note says do not treat as clearance", "clearance" in r["note"].lower())


def test_all_branches_never_opine():
    for status in ("REGISTERED", "WITHDRAWN", "NOT_REGISTERED"):
        _patch(_sec(status))
        r = fp.verify_portal(cik="1666102", file_number="007-00042")
        assert_true(f"{status} → never-opine state", r["state"] in NEVER_OPINE, f"got {r['state']!r}")


def main():
    test_normalize_file_number()
    test_parse_finra_entry_found()
    test_parse_finra_entry_not_found()
    test_parse_finra_entry_does_not_collide()
    test_verify_satisfied()
    test_verify_withdrawn_escalates()
    test_verify_not_registered_escalates()
    test_verify_sec_registered_but_not_on_finra()
    test_verify_name_mismatch_escalates()
    test_verify_source_unreachable_is_open()
    test_all_branches_never_opine()
    print("\nAll FINRA portal-check tests passed.")


if __name__ == "__main__":
    main()
