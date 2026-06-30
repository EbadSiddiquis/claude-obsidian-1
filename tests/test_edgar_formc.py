#!/usr/bin/env python3
"""test_edgar_formc.py — hermetic tests for the Form C driver.

Covers scripts/edgar_formd.py:parse_form_c and the Regulation-Crowdfunding evaluators in
scripts/control-panel.py (cf_cap, cf_form_c_filed, cf_intermediary), plus the never-opine
invariant that none of them emit a legal conclusion. Feeds a canned Form C XML through the
parser (no network, no SEC fetch) and asserts both the parsed fields and each evaluator's
(state, note). Pure stdlib.

Usage:
  python3 tests/test_edgar_formc.py
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))  # so control-panel.py can `import edgar_formd as efd`


def _load(modname, filename):
    spec = importlib.util.spec_from_file_location(modname, SCRIPTS / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


efd = _load("edgar_formd", "edgar_formd.py")
cp = _load("control_panel", "control-panel.py")


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


# A trimmed but structurally faithful Form C primary_doc.xml: namespaced root, com:-prefixed
# address, the intermediary block (companyName / commissionCik / commissionFileNumber / crdNumber)
# as siblings of issuerInfo under issuerInformation, signaturePerson, and a jurisdiction list.
FORM_C_XML = """<?xml version="1.0" encoding="UTF-8"?>
<edgarSubmission xmlns="http://www.sec.gov/edgar/formc" xmlns:com="http://www.sec.gov/edgar/common">
  <headerData><submissionType>C</submissionType></headerData>
  <formData>
    <issuerInformation>
      <issuerInfo>
        <nameOfIssuer>Acme Widgets, Inc.</nameOfIssuer>
        <legalStatus><legalStatusForm>Corporation</legalStatusForm><jurisdictionOrganization>DE</jurisdictionOrganization></legalStatus>
        <issuerAddress><com:city>Austin</com:city><com:stateOrCountry>TX</com:stateOrCountry></issuerAddress>
      </issuerInfo>
      <isCoIssuer>N</isCoIssuer>
      <companyName>Honest Portal LLC</companyName>
      <commissionCik>0001234567</commissionCik>
      <commissionFileNumber>007-00099</commissionFileNumber>
      <crdNumber>299999</crdNumber>
    </issuerInformation>
    <offeringInformation>
      <securityOfferedType>Common Stock</securityOfferedType>
      <offeringAmount>10000.00</offeringAmount>
      <maximumOfferingAmount>500000.00</maximumOfferingAmount>
      <deadlineDate>12-31-2026</deadlineDate>
    </offeringInformation>
    <annualReportDisclosureRequirements>
      <issueJurisdictionSecuritiesOffering>CA</issueJurisdictionSecuritiesOffering>
      <issueJurisdictionSecuritiesOffering>TX</issueJurisdictionSecuritiesOffering>
    </annualReportDisclosureRequirements>
    <signatureInfo>
      <signaturePersons>
        <signaturePerson>
          <personSignature>Jane Q Founder</personSignature>
          <personTitle>Chief Executive Officer</personTitle>
        </signaturePerson>
      </signaturePersons>
    </signatureInfo>
  </formData>
</edgarSubmission>"""

# A second issuer with a maximum over the $5M Reg CF ceiling (cf_cap escalate branch).
FORM_C_XML_OVER_CAP = FORM_C_XML.replace("<maximumOfferingAmount>500000.00", "<maximumOfferingAmount>6000000.00")

NEVER_OPINE_STATES = {"satisfied", "open", "escalate_to_counsel", "n/a", "satisfied_by_counsel"}


def _eval(eval_key, fd):
    """Run one control through control-panel's evaluate() (ctx unused by the cf_* evaluators)."""
    control = {"eval": eval_key}
    return cp.evaluate(control, fd, {})


def _eval_ctx(eval_key, ctx, fd=None):
    return cp.evaluate({"eval": eval_key}, fd or {}, ctx)


def _fc(state="open", has_cfportal=True, custodian="North Capital Private Securities Corporation",
        comp="a percentage of gross proceeds; may take an equity position in an issuer", affirmative=None):
    return {"fund_custody": {"state": state, "custody": {
        "has_cfportal": has_cfportal, "custodian_name": custodian,
        "compensation_desc": comp, "affirmative_disclosures": affirmative or []}}}


# ─── parse_form_c ────────────────────────────────────────────────────────────
def test_parse_form_c_fields():
    fd = efd.parse_form_c(FORM_C_XML)
    assert_eq("issuer (nameOfIssuer, not the portal's companyName)", "Acme Widgets, Inc.", fd["issuer"])
    assert_eq("intermediary_name scoped to issuerInformation", "Honest Portal LLC", fd["intermediary_name"])
    assert_eq("intermediary_cik", "0001234567", fd["intermediary_cik"])
    assert_eq("intermediary_file_number (007- portal)", "007-00099", fd["intermediary_file_number"])
    assert_eq("intermediary_crd", "299999", fd["intermediary_crd"])
    assert_eq("offering target", "10000.00", fd["offering_amount"])
    assert_eq("offering maximum", "500000.00", fd["maximum_offering_amount"])
    assert_eq("deadline", "12-31-2026", fd["deadline_date"])
    assert_eq("state jurisdictions", ["CA", "TX"], fd["state_jurisdictions"])
    assert_eq("signature persons → covered persons", ["Jane Q Founder"],
              [p["name"] for p in fd["related_persons"]])
    assert_eq("covered-person role", ["Chief Executive Officer"], fd["related_persons"][0]["relationships"])


# ─── cf_cap: within ceiling → open (never concludes from one filing) ─────────
def test_cf_cap_within_ceiling_is_open():
    fd = efd.parse_form_c(FORM_C_XML)
    state, _ev, note = _eval("cf_cap", fd)
    assert_eq("cf_cap within $5M ceiling → open", "open", state)
    assert_true("cf_cap note flags the rolling-aggregate caveat", "ROLLING" in note.upper())


# ─── cf_cap: over ceiling → escalate ─────────────────────────────────────────
def test_cf_cap_over_ceiling_escalates():
    fd = efd.parse_form_c(FORM_C_XML_OVER_CAP)
    state, _ev, note = _eval("cf_cap", fd)
    assert_eq("cf_cap maximum > $5M → escalate_to_counsel", "escalate_to_counsel", state)
    assert_true("cf_cap escalate note says EXCEEDS", "EXCEEDS" in note)


# ─── cf_cap: maximum unparseable → falls back to target ──────────────────────
def test_cf_cap_falls_back_to_target():
    fd = efd.parse_form_c(FORM_C_XML)
    fd["maximum_offering_amount"] = None  # simulate a missing/malformed maximum
    state, _ev, note = _eval("cf_cap", fd)
    assert_eq("cf_cap with no maximum still evaluates the target → open", "open", state)
    assert_true("cf_cap note names the target fallback", "target" in note)


# ─── cf_form_c_filed: existence verified but multi-part obligation → open ────
def test_cf_form_c_filed_is_open_not_satisfied():
    fd = efd.parse_form_c(FORM_C_XML)
    fd["accession"] = "0001234567-26-000001"
    fd["form_type"] = "C"
    state, _ev, note = _eval("cf_form_c_filed", fd)
    # Mirrors the Form D precedent: a partly-unverified exemption-fatal obligation is never "satisfied".
    assert_eq("cf_form_c_filed → open (not satisfied)", "open", state)
    assert_true("cf_form_c_filed note says NOT a clearance", "NOT a clearance" in note)


# ─── cf_intermediary: surfaces the portal; 007- prefix recognised ────────────
def test_cf_intermediary_surfaces_portal():
    fd = efd.parse_form_c(FORM_C_XML)
    state, ev, note = _eval("cf_intermediary", fd)
    assert_eq("cf_intermediary → open (FINRA membership not auto-verified)", "open", state)
    assert_true("cf_intermediary evidence names the portal", any("Honest Portal LLC" in e for e in ev))
    assert_true("cf_intermediary recognises the 007- funding-portal prefix", "funding-portal file number" in note)


# ─── never-opine invariant across every cf_* evaluator ───────────────────────
def test_cf_evaluators_never_opine():
    fd = efd.parse_form_c(FORM_C_XML)
    fd["accession"] = "0001234567-26-000001"
    fd["form_type"] = "C"
    for key in ("cf_cap", "cf_form_c_filed", "cf_intermediary"):
        state, _ev, _note = _eval(key, fd)
        assert_true(f"{key} resolves to a never-opine state", state in NEVER_OPINE_STATES,
                    f"got {state!r}")


# ─── portal_conduct (FINRA prohibited-conduct / FP Rule 200) ─────────────────
def test_portal_conduct_clean_open_and_does_not_flag_comp():
    state, ev, note = _eval_ctx("portal_conduct", _fc())
    assert_eq("clean portal → open", "open", state)
    assert_true("funds-handling prong cross-referenced", any("funds-handling prong" in e for e in ev))
    assert_true("compensation surfaced as evidence", any("compensation" in e.lower() for e in ev))
    # The discipline test: permitted transaction-based / equity comp must be SURFACED, never flagged.
    assert_true("does not opine on compensation permissibility",
                "legal judgment for counsel" in note and "NOT the system" in note)


def test_portal_conduct_affirmative_disclosure_escalates():
    state, ev, note = _eval_ctx("portal_conduct", _fc(affirmative=["isOrderAgainst"]))
    assert_eq("portal self-disclosed a regulatory event → escalate", "escalate_to_counsel", state)
    assert_true("note cites FP Rule 200", "FP Rule 200" in note)


def test_portal_conduct_funds_flagged_escalates():
    state, _ev, _note = _eval_ctx("portal_conduct", _fc(state="escalate_to_counsel", custodian="Ksdaq Inc."))
    assert_eq("funds-handling prong flagged → escalate", "escalate_to_counsel", state)


def test_portal_conduct_withdrawn_cites_right_reason():
    # A withdrawn portal escalates because it is DEREGISTERED, not because it handles funds.
    ctx = {"fund_custody": {"state": "escalate_to_counsel", "custody": {
        "has_cfportal": True, "withdrawn": True, "custodian_name": None,
        "compensation_desc": None, "affirmative_disclosures": []}}}
    state, ev, note = _eval_ctx("portal_conduct", ctx)
    assert_eq("withdrawn → escalate", "escalate_to_counsel", state)
    assert_true("evidence cites withdrawal, not fund-handling", any("WITHDRAWN" in e for e in ev))
    assert_true("evidence does NOT misattribute to fund-handling",
                not any("may handle investor funds" in e for e in ev))
    assert_true("note cites withdrawal", "WITHDRAWN" in note)


def test_portal_conduct_no_cfportal_open():
    state, _ev, _note = _eval_ctx("portal_conduct", {"fund_custody": {"state": "open", "custody": {"has_cfportal": False}}})
    assert_eq("no CFPORTAL → open (unevidenced)", "open", state)
    # also tolerate a totally absent fund_custody ctx
    assert_eq("missing fund_custody ctx → open", "open", _eval_ctx("portal_conduct", {})[0])


def test_portal_conduct_never_opine():
    for ctx in (_fc(), _fc(affirmative=["isEnjoined"]), _fc(state="escalate_to_counsel"),
                {"fund_custody": {"state": "open", "custody": {"has_cfportal": False}}}):
        assert_true("portal_conduct never-opine", _eval_ctx("portal_conduct", ctx)[0] in NEVER_OPINE_STATES)


# ─── cf_single_intermediary (227.300(b)) + the concurrency cross-check ───────
def _ix_ctx(rows, truncated=False):
    return {"form_c_intermediaries": {"rows": rows, "truncated": truncated}}


def _row(cik, name, date, deadline=None, form="C"):
    return {"form": form, "date": date, "accession": f"acc-{cik}-{date}",
            "intermediary_cik": cik, "intermediary_name": name, "deadline_date": deadline}


def test_concurrent_overlap_detection():
    over = [_row("111", "A", "2026-01-01", "12-31-2026"), _row("222", "B", "2026-06-01", "12-31-2026")]
    assert_true("distinct + overlapping windows → concurrent", cp._concurrent_distinct_intermediaries(over))
    seq = [_row("111", "A", "2022-01-01", "06-30-2022"), _row("222", "B", "2024-01-01", "06-30-2024")]
    assert_true("distinct + non-overlapping → not concurrent", not cp._concurrent_distinct_intermediaries(seq))
    same = [_row("111", "A", "2026-01-01", "12-31-2026"), _row("111", "A", "2026-02-01", None)]
    assert_true("same intermediary is never concurrent", not cp._concurrent_distinct_intermediaries(same))
    open_end = [_row("111", "A", "2026-01-01", None), _row("222", "B", "2026-03-01", None)]
    assert_true("missing end-date → conservative overlap (escalate-safe)", cp._concurrent_distinct_intermediaries(open_end))


def test_cf_single_intermediary_one_is_open():
    state, ev, note = _eval_ctx("cf_single_intermediary", _ix_ctx([_row("111", "Mr. Crowd", "2026-06-29", "12-31-2026")]))
    assert_eq("one intermediary → open", "open", state)
    assert_true("note cites single intermediary", "single intermediary" in note)
    assert_true("evidence lists the filing", any("Mr. Crowd" in e for e in ev))


def test_cf_single_intermediary_concurrent_escalates():
    rows = [_row("111", "A", "2026-01-01", "12-31-2026"), _row("222", "B", "2026-06-01", "12-31-2026")]
    state, _ev, note = _eval_ctx("cf_single_intermediary", _ix_ctx(rows))
    assert_eq("distinct + overlapping → escalate", "escalate_to_counsel", state)
    assert_true("note cites 227.300(b)", "227.300(b)" in note)


def test_cf_single_intermediary_sequential_is_open():
    rows = [_row("111", "A", "2022-01-01", "06-30-2022"), _row("222", "B", "2024-01-01", "06-30-2024")]
    state, _ev, note = _eval_ctx("cf_single_intermediary", _ix_ctx(rows))
    assert_eq("distinct + sequential → open (permitted)", "open", state)
    assert_true("note says sequential", "SEQUENTIAL" in note.upper())


def test_cf_single_intermediary_no_scan_open():
    assert_eq("missing scan ctx → open fallback", "open", _eval_ctx("cf_single_intermediary", {})[0])


def test_cf_single_intermediary_truncation_blocks_clean_clearance():
    # Truncated scan + one intermediary seen: must NOT claim a clean single-intermediary record.
    _state, ev, note = _eval_ctx("cf_single_intermediary", _ix_ctx([_row("111", "A", "2026-01-01")], truncated=True))
    assert_true("truncation surfaced (no silent cap)", any("only the most recent" in e for e in ev))
    assert_true("note refuses a full-record confirmation when truncated", "INCOMPLETE" in note)
    assert_true("note does NOT claim 'all name a single intermediary'", "all name a single intermediary" not in note)


def test_cf_single_intermediary_parse_gap_blocks_clean_clearance():
    # 2 Form C / C-A filings exist on the issuer, but only 1 parsed into rows -> incomplete.
    fd = {"all_filings": [{"form": "C", "date": "2026-06-29", "accession": "a1"},
                          {"form": "C/A", "date": "2026-05-01", "accession": "a2"}]}
    _state, ev, note = _eval_ctx("cf_single_intermediary", _ix_ctx([_row("111", "A", "2026-06-29")]), fd)
    assert_true("parse gap surfaced", any("could not be parsed" in e for e in ev))
    assert_true("note refuses clean clearance on a parse gap", "INCOMPLETE" in note)


def test_cf_single_intermediary_unresolved_intermediary_blocks_clearance():
    # All scanned rows fail to resolve an intermediary → must say "could not identify", never claim one.
    nullrow = {"form": "C", "date": "2026-06-29", "accession": "a",
               "intermediary_cik": None, "intermediary_name": None, "intermediary_file_number": None}
    _state, _ev, note = _eval_ctx("cf_single_intermediary", _ix_ctx([nullrow]))
    assert_true("unresolved → not a confirmation of a single intermediary", "NOT a confirmation" in note)
    assert_true("does not claim a single intermediary record", "all name a single intermediary" not in note)


def test_cf_single_intermediary_one_good_one_unresolved_is_incomplete():
    # One resolved + one unresolved row (single distinct seen, but a gap) → INCOMPLETE, not clean.
    good = _row("111", "Mr. Crowd", "2026-06-29", "12-31-2026")
    nullrow = {"form": "C/A", "date": "2026-05-01", "accession": "b",
               "intermediary_cik": None, "intermediary_name": None, "intermediary_file_number": None}
    _state, _ev, note = _eval_ctx("cf_single_intermediary", _ix_ctx([good, nullrow]))
    assert_true("mixed resolved/unresolved → INCOMPLETE", "INCOMPLETE" in note)


def test_cf_single_intermediary_distinct_by_file_number_when_cik_null():
    # Distinctness must not rely on CIK alone: two filings with null CIK but different file numbers
    # are two intermediaries (overlapping windows here → escalate), not one.
    a = {"form": "C", "date": "2026-01-01", "accession": "a", "intermediary_cik": None,
         "intermediary_name": "A", "intermediary_file_number": "007-00001", "deadline_date": "12-31-2026"}
    b = {"form": "C", "date": "2026-06-01", "accession": "b", "intermediary_cik": None,
         "intermediary_name": "B", "intermediary_file_number": "007-00002", "deadline_date": "12-31-2026"}
    state, _ev, _note = _eval_ctx("cf_single_intermediary", _ix_ctx([a, b]))
    assert_eq("distinct by file number (null CIK) + overlap → escalate", "escalate_to_counsel", state)


def test_cf_single_intermediary_never_opine():
    for ctx in (_ix_ctx([_row("111", "A", "2026-01-01", "12-31-2026")]),
                _ix_ctx([_row("111", "A", "2026-01-01", "12-31-2026"), _row("222", "B", "2026-06-01", "12-31-2026")]),
                {}):
        assert_true("cf_single_intermediary never-opine", _eval_ctx("cf_single_intermediary", ctx)[0] in NEVER_OPINE_STATES)


def test_list_form_c_intermediaries_scopes_and_caps():
    orig = efd.fetch_archive_doc
    efd.fetch_archive_doc = lambda *a, **k: FORM_C_XML  # canned Form C (intermediary 'Honest Portal LLC')
    try:
        all_filings = [{"form": "C", "date": "2026-06-29", "accession": "a1", "primary_document": "xslC_X01/primary_doc.xml"},
                       {"form": "D", "date": "2025-01-01", "accession": "aD", "primary_document": "x"},
                       {"form": "C/A", "date": "2026-05-01", "accession": "a2", "primary_document": "xslC_X01/primary_doc.xml"}]
        rows, trunc = efd.list_form_c_intermediaries("123", all_filings)
        assert_eq("only C / C-A filings scanned (Form D skipped)", 2, len(rows))
        assert_eq("intermediary parsed from each", "Honest Portal LLC", rows[0]["intermediary_name"])
        assert_true("not truncated under cap", not trunc)
        rows2, trunc2 = efd.list_form_c_intermediaries("123", all_filings, cap=1)
        assert_eq("cap respected", 1, len(rows2))
        assert_true("truncation flagged", trunc2)
    finally:
        efd.fetch_archive_doc = orig


def test_list_form_c_intermediaries_derives_raw_doc_basename():
    seen = []
    orig = efd.fetch_archive_doc
    efd.fetch_archive_doc = lambda cik, acc, doc: (seen.append(doc), FORM_C_XML)[1]
    try:
        efd.list_form_c_intermediaries("123", [{"form": "C", "date": "2026-06-29", "accession": "a1",
                                                "primary_document": "xslC_X01/primary_doc.xml"}])
        assert_eq("raw-XML basename derived from primaryDocument (not hardcoded)", "primary_doc.xml", seen[0])
    finally:
        efd.fetch_archive_doc = orig


def test_list_form_c_intermediaries_skips_failed_fetch_not_crash():
    # sec_fetch sys.exits (SystemExit) on a failed fetch; one bad filing must be skipped, not abort.
    orig = efd.fetch_archive_doc
    def flaky(cik, acc, doc):
        if acc == "bad":
            raise SystemExit("fetch failed (404)")
        return FORM_C_XML
    efd.fetch_archive_doc = flaky
    try:
        all_filings = [{"form": "C", "date": "2026-06-29", "accession": "good", "primary_document": "xslC_X01/primary_doc.xml"},
                       {"form": "C/A", "date": "2026-05-01", "accession": "bad", "primary_document": "xslC_X01/primary_doc.xml"}]
        rows, _trunc = efd.list_form_c_intermediaries("123", all_filings)
        assert_eq("failed fetch skipped (SystemExit caught), not a crash", 1, len(rows))
    finally:
        efd.fetch_archive_doc = orig


def main():
    test_concurrent_overlap_detection()
    test_cf_single_intermediary_one_is_open()
    test_cf_single_intermediary_concurrent_escalates()
    test_cf_single_intermediary_sequential_is_open()
    test_cf_single_intermediary_no_scan_open()
    test_cf_single_intermediary_truncation_blocks_clean_clearance()
    test_cf_single_intermediary_parse_gap_blocks_clean_clearance()
    test_cf_single_intermediary_unresolved_intermediary_blocks_clearance()
    test_cf_single_intermediary_one_good_one_unresolved_is_incomplete()
    test_cf_single_intermediary_distinct_by_file_number_when_cik_null()
    test_cf_single_intermediary_never_opine()
    test_list_form_c_intermediaries_scopes_and_caps()
    test_list_form_c_intermediaries_derives_raw_doc_basename()
    test_list_form_c_intermediaries_skips_failed_fetch_not_crash()
    test_portal_conduct_clean_open_and_does_not_flag_comp()
    test_portal_conduct_affirmative_disclosure_escalates()
    test_portal_conduct_funds_flagged_escalates()
    test_portal_conduct_withdrawn_cites_right_reason()
    test_portal_conduct_no_cfportal_open()
    test_portal_conduct_never_opine()
    test_parse_form_c_fields()
    test_cf_cap_within_ceiling_is_open()
    test_cf_cap_over_ceiling_escalates()
    test_cf_cap_falls_back_to_target()
    test_cf_form_c_filed_is_open_not_satisfied()
    test_cf_intermediary_surfaces_portal()
    test_cf_evaluators_never_opine()
    print("\nAll Form C driver tests passed.")


if __name__ == "__main__":
    main()
