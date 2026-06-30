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


def main():
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
