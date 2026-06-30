#!/usr/bin/env python3
"""assumption-check.py - verify the system's own assumptions (authority-model Tier F).

The evaluators rely on truths about EDGAR/eCFR/FR/RSS shapes and codes. If one silently breaks,
a control's state goes wrong without any error. This runs each 'verifiable' assumption's executable
check against live data and reports holds / VIOLATED / unverifiable; a VIOLATED assumption is a
drift event that flags the controls it could corrupt. 'accepted' assumptions (known limitations /
heuristics) are listed separately so they stay visible.

Never concludes about a deal - this is the system checking ITSELF.

USAGE
  export SEC_CONTACT_EMAIL="you@example.com"
  python3 scripts/assumption-check.py
  python3 scripts/assumption-check.py --json
"""
import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys

import assumption_registry as asm
import edgar_formd as efd

HERE = os.path.dirname(os.path.abspath(__file__))
UA = os.environ.get("EDGAR_USER_AGENT", "claude-obsidian-research " + os.environ.get("SEC_CONTACT_EMAIL", "set-SEC_CONTACT_EMAIL@example.com"))
REF_CIK = "2141182"  # a stable filer with a Form D, used as the self-test fixture
REF_FORMC_CIK = "2140631"  # 20Slash20, Inc. - a stable Form C filer (via the Mr. Crowd portal)
REF_PORTAL_CIK = "1666102"  # Ksdaq Inc. / Mr. Crowd - a stable funding portal (CFPORTAL since 2016), file 007-00042

# finra-portal-check has a hyphenated filename -> load it by path to reuse its real fetch+parse.
_fp_spec = importlib.util.spec_from_file_location("finra_portal_check", os.path.join(HERE, "finra-portal-check.py"))
finra_portal = importlib.util.module_from_spec(_fp_spec)
_fp_spec.loader.exec_module(finra_portal)

_fc_spec = importlib.util.spec_from_file_location("fund_custody_check", os.path.join(HERE, "fund-custody-check.py"))
fund_custody = importlib.util.module_from_spec(_fc_spec)
_fc_spec.loader.exec_module(fund_custody)


def _curl(url):
    out = subprocess.run(["curl", "-sSL", "-A", UA, url], capture_output=True, text=True)
    return out.stdout if out.returncode == 0 else None


def _ctx():
    ctx = {}
    try:
        ctx["fd"] = efd.load_form_d(REF_CIK)
    except SystemExit as e:
        ctx["fd_error"] = str(e)
    try:
        ctx["fc"] = efd.load_form_c(REF_FORMC_CIK)
    except SystemExit as e:
        ctx["fc_error"] = str(e)
    return ctx


CHECKS = {}
def check(name):
    def deco(fn):
        CHECKS[name] = fn
        return fn
    return deco


@check("formd_raw_xml")
def _formd_raw_xml(ctx):
    fd = ctx.get("fd")
    if not fd:
        return None, "could not load reference Form D"
    ok = bool(fd.get("issuer")) and bool(fd.get("exemptions"))
    return ok, f"issuer={fd.get('issuer')!r} exemptions={fd.get('exemptions')}"


@check("formd_fields")
def _formd_fields(ctx):
    fd = ctx.get("fd")
    if not fd:
        return None, "could not load reference Form D"
    ok = bool(fd.get("related_persons")) and fd.get("has_non_accredited") is not None and bool(fd.get("date_of_first_sale"))
    return ok, f"related_persons={len(fd.get('related_persons') or [])} has_non_accredited={fd.get('has_non_accredited')} first_sale={fd.get('date_of_first_sale')}"


@check("formc_raw_xml")
def _formc_raw_xml(ctx):
    fc = ctx.get("fc")
    if not fc:
        return None, "could not load reference Form C"
    ok = bool(fc.get("issuer")) and bool(fc.get("intermediary_cik"))
    return ok, f"issuer={fc.get('issuer')!r} intermediary_cik={fc.get('intermediary_cik')}"


@check("formc_fields")
def _formc_fields(ctx):
    fc = ctx.get("fc")
    if not fc:
        return None, "could not load reference Form C"
    ok = (bool(fc.get("intermediary_file_number")) and fc.get("maximum_offering_amount") is not None
          and bool(fc.get("state_jurisdictions")) and bool(fc.get("related_persons")))
    return ok, (f"file_number={fc.get('intermediary_file_number')} max={fc.get('maximum_offering_amount')} "
                f"states={len(fc.get('state_jurisdictions') or [])} signers={len(fc.get('related_persons') or [])}")


@check("exemption_code_06b")
def _exemption_code_06b(ctx):
    fd = ctx.get("fd")
    if not fd:
        return None, "could not load reference Form D"
    return "06b" in (fd.get("exemptions") or []), f"exemptions={fd.get('exemptions')}"


@check("ecfr_shape")
def _ecfr_shape(ctx):
    raw = _curl("https://www.ecfr.gov/api/versioner/v1/versions/title-17.json?part=230")
    if not raw:
        return None, "fetch failed"
    try:
        cv = json.loads(raw).get("content_versions", [])
    except json.JSONDecodeError:
        return None, "non-JSON response"
    ok = any(v.get("identifier") == "230.506" and v.get("amendment_date") for v in cv)
    return ok, f"content_versions={len(cv)}; 230.506 present={ok}"


@check("fedreg_shape")
def _fedreg_shape(ctx):
    raw = _curl("https://www.federalregister.gov/api/v1/documents.json?per_page=1&order=newest"
                "&conditions%5Bagencies%5D%5B%5D=securities-and-exchange-commission"
                "&fields%5B%5D=cfr_references&fields%5B%5D=title")
    if not raw:
        return None, "fetch failed"
    try:
        res = json.loads(raw).get("results", [])
    except json.JSONDecodeError:
        return None, "non-JSON response"
    ok = bool(res) and "cfr_references" in res[0]
    return ok, f"results={len(res)}; cfr_references field present={ok}"


@check("ap_rss_shape")
def _ap_rss_shape(ctx):
    raw = _curl("https://www.sec.gov/rss/litigation/admin.xml")
    if not raw:
        return None, "fetch failed"
    items = re.findall(r"<item>(.*?)</item>", raw, re.S)
    titled = [b for b in items if re.search(r"<title>.*?</title>", b, re.S)]
    return len(titled) >= 1, f"items={len(items)} with-title={len(titled)}"


@check("cfportal_forms")
def _cfportal_forms(ctx):
    try:
        subs = efd.fetch_submissions(REF_PORTAL_CIK)
    except SystemExit as e:
        return None, f"fetch failed: {e}"
    forms = subs.get("filings", {}).get("recent", {}).get("form", [])
    cfp = [f for f in forms if f.upper().startswith("CFPORTAL")]
    return len(cfp) >= 1, f"reference portal CIK {REF_PORTAL_CIK} ({subs.get('name')!r}): {len(cfp)} CFPORTAL-family filing(s), e.g. {cfp[:3]}"


@check("finra_fp_shape")
def _finra_fp_shape(ctx):
    try:
        html = finra_portal.fetch_finra_list()
    except Exception as e:  # RuntimeError on fetch failure, or curl absent
        return None, f"fetch failed: {e}"
    entry = finra_portal.parse_finra_entry(html, "007-00042")  # Ksdaq/Mr. Crowd, file 7-42
    ok = bool(entry.get("found")) and bool(entry.get("legal_name"))
    return ok, f"div.multicolumn-container entries parseable; file 7-42 -> {entry.get('legal_name')!r}"


@check("cfportal_escrow_fields")
def _cfportal_escrow_fields(ctx):
    try:
        cust = fund_custody.load_portal_custody(REF_PORTAL_CIK)
    except SystemExit as e:
        return None, f"fetch failed: {e}"
    if not cust.get("has_cfportal"):
        return False, f"reference portal CIK {REF_PORTAL_CIK} has no CFPORTAL on file"
    bd = fund_custody.verify_custodian_is_bd(cust.get("custodian_name"))
    ok = bool(cust.get("custodian_name")) and bool(bd.get("is_registered_bd"))
    return ok, f"custodian={cust.get('custodian_name')!r}; registered-BD={bd.get('is_registered_bd')}"


@check("cfportal_disclosure_fields")
def _cfportal_disclosure_fields(ctx):
    try:
        cust = fund_custody.load_portal_custody(REF_PORTAL_CIK)
    except SystemExit as e:
        return None, f"fetch failed: {e}"
    if not cust.get("has_cfportal") or cust.get("withdrawn"):
        return None, f"reference portal CIK {REF_PORTAL_CIK} has no live CFPORTAL"
    seen = cust.get("disclosure_subtrees_seen", 0)
    # The negative-event subtrees must still be present (else the scan silently sees nothing).
    return seen >= 1, f"disclosure subtrees present={seen}; affirmative={cust.get('affirmative_disclosures')}"


def main():
    ap = argparse.ArgumentParser(description="Verify the system's own assumptions (Tier F meta-node).")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    assumptions = asm.load_assumptions()
    ctx = _ctx()
    results = []
    for a in assumptions:
        if a["kind"] == "accepted":
            results.append({"id": a["id"], "kind": "accepted", "status": "accepted", "detail": a["statement"], "affected": []})
            continue
        fn = CHECKS.get(a.get("check"))
        if not fn:
            results.append({"id": a["id"], "kind": "verifiable", "status": "unverifiable", "detail": "no checker", "affected": []})
            continue
        holds, detail = fn(ctx)
        status = "holds" if holds else ("unverifiable" if holds is None else "VIOLATED")
        results.append({"id": a["id"], "kind": "verifiable", "status": status, "detail": detail,
                        "affected": a.get("affects_controls", []) if status == "VIOLATED" else []})

    violated = [r for r in results if r["status"] == "VIOLATED"]
    if args.json:
        print(json.dumps({"violated": len(violated), "results": results}, indent=2))
        return

    print(f"System-assumption check (Tier F) | {len(assumptions)} assumptions | VIOLATED: {len(violated)}\n")
    for r in results:
        print(f"  [{r['status']:>12}] {r['id']}")
        print(f"        {r['detail']}")
        for c in r["affected"]:
            print(f"        SUSPECT control (assumption violated): {c}")
    if violated:
        print(f"\n{len(violated)} assumption(s) VIOLATED -> the dependent controls may be silently wrong. Fix the evaluator before trusting their state.")
    else:
        print("\nAll verifiable assumptions hold. Accepted limitations are listed above and remain by design.")


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        try:
            sys.stdout.close()
        except Exception:
            pass
