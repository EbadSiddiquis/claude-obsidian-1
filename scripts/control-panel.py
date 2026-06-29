#!/usr/bin/env python3
"""control-panel.py - render the §506(b) counsel-ready control panel for a CIK.

Reads the control framework (controls/reg-d-506b.json), loads the issuer's Form D, computes
each control's state from public data where possible, and marks the rest honestly. The whole
checklist a lawyer would look at - not just the bad-actor row.

THE DISCIPLINE: assembles and flags; never concludes. Each control resolves to
satisfied / open / escalate_to_counsel / n/a, with a citation and a note. Counsel opines.

USAGE
  export SEC_CONTACT_EMAIL="you@example.com"
  python3 scripts/control-panel.py --cik 2141182
  python3 scripts/control-panel.py --cik 2141182 --json
"""
import argparse
import json
import os
import subprocess
import sys

import edgar_formd as efd

HERE = os.path.dirname(os.path.abspath(__file__))
CONTROLS = os.path.join(os.path.dirname(HERE), "controls", "reg-d-506b.json")


def run_badactor(names):
    out = subprocess.run(
        ["python3", os.path.join(HERE, "badactor-watch.py"), "--names", "; ".join(names), "--json"],
        capture_output=True, text=True, env={**os.environ})
    if out.returncode != 0:
        sys.exit(f"badactor-watch failed ({out.returncode}): {out.stderr.strip()}")
    return json.loads(out.stdout)


def evaluate(control, fd, ctx):
    """Return (state, evidence, note) for one control given parsed Form D `fd` and shared ctx."""
    key = control["eval"]

    if key == "exemption_is_506b":
        ex = fd.get("exemptions") or []
        if "06b" in ex:
            return "satisfied", [f"Form D federalExemptionsExclusions = {ex}"], "Form D claims Rule 506(b) [06b]."
        if "06c" in ex:
            return "escalate_to_counsel", [f"Form D = {ex}"], "Form D claims 506(c), not 506(b) - wrong control set? Confirm with counsel."
        return "open", [f"Form D = {ex}"], "Rule 506(b) not clearly claimed on Form D; confirm the exemption relied upon."

    if key == "nonaccredited_ceiling":
        na = fd.get("has_non_accredited")
        if na is False:
            return "satisfied", ["Form D: hasNonAccreditedInvestors = false"], "Form D reports 0 non-accredited purchasers; the <=35 ceiling is not implicated (counsel confirms reliance)."
        if na is True:
            return "open", ["Form D: hasNonAccreditedInvestors = true"], "Non-accredited purchasers present; confirm count <=35 AND each is sophisticated (private)."
        return "open", [], "Non-accredited status not determinable from Form D; confirm (private)."

    if key == "info_delivery_conditional":
        if fd.get("has_non_accredited") is False:
            return "n/a", ["Form D: 0 non-accredited"], "Not triggered: no non-accredited purchasers per Form D."
        return "open", [], "If any non-accredited purchaser, confirm 230.502(b) information delivery (private)."

    if key == "no_general_solicitation":
        return "escalate_to_counsel", [], "The defining 506(b) risk. Not verifiable from EDGAR - needs marketing-conduct evidence; counsel assesses."

    if key == "bad_actor_screen":
        flagged = [r for r in ctx["badactor"]["results"] if r["state"] == "escalate_to_counsel"]
        if flagged:
            ev = [f"{r['watch_name']}: {r['evidence'][0]['title'][:70]}" for r in flagged]
            return "escalate_to_counsel", ev, "Covered person(s) appear in a current SEC administrative proceeding - DISAMBIGUATE + assess 506(d) coverage; counsel opines."
        return "open", [f"screened {len(ctx['watchlist'])} covered persons vs AP feed; no current match"], "No match in the AP-feed window. NOT a clearance - historical check (SALI/archives) still required."

    if key == "form_d_filed":
        fs = fd.get("date_of_first_sale")
        return "open", [f"Form D on file: accession {fd.get('accession')}", f"first-sale date: {fs}"], \
            "Form D is filed; confirm it was within 15 days of first sale (reconcile first-sale date vs filing date)."

    if key == "amount_reconciliation":
        ev = [f"Form D offered: {fd.get('total_offering_amount')}", f"sold: {fd.get('total_sold')}", f"remaining: {fd.get('total_remaining')}"]
        return "open", ev, "Reconcile these Form D amounts against the cap table / subscription records (private)."

    if key == "manual_hybrid":
        return "open", [], "Public-side checkable (other EDGAR offerings within the integration window) + private facts; not yet wired."
    if key == "manual_runnable":
        return "open", [], "Runnable against court-order / enforcement data; not yet wired."
    if key == "manual_continuous":
        return "open", [], "Monitor on a schedule (continuous)."
    # default: manual_private
    return "open", [], "Needs internal evidence; counsel confirms."


def main():
    ap = argparse.ArgumentParser(description="Render the Rule 506(b) counsel-ready control panel for a CIK (never-opine).")
    ap.add_argument("--cik", required=True)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    framework = json.load(open(CONTROLS, encoding="utf-8"))
    fd = efd.load_form_d(args.cik)
    watchlist = [fd["issuer"]] + [p["name"] for p in fd["related_persons"]]
    ctx = {"watchlist": watchlist, "badactor": run_badactor(watchlist)}

    rows = []
    for c in framework["controls"]:
        state, evidence, note = evaluate(c, fd, ctx)
        rows.append({**c, "state": state, "evidence": evidence, "note": note})

    counts = {}
    for r in rows:
        counts[r["state"]] = counts.get(r["state"], 0) + 1
    urgent = [r for r in rows if r["severity"] == "exemption_fatal" and r["state"] in ("open", "escalate_to_counsel")]

    if args.json:
        print(json.dumps({"issuer": fd["issuer"], "cik": str(int(args.cik)), "form_d": fd.get("accession"),
                          "offering_type": framework["offering_type"], "counts": counts,
                          "exemption_fatal_open": [r["id"] for r in urgent], "controls": rows}, indent=2))
        return

    MARK = {"satisfied": "OK ", "open": "open", "escalate_to_counsel": "FLAG->counsel", "n/a": "n/a "}
    print(f"Counsel-ready control panel | {framework['offering_type']} | {fd['issuer']} | CIK {int(args.cik)} | Form D {fd.get('accession')}")
    summary = " · ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
    print(f"{summary} · conclusions drawn: 0\n")
    for r in rows:
        print(f"[{MARK[r['state']]:>13}] {r['id']}  ({r['severity']}, {r['locus']}, owner={r['owner']})")
        print(f"                {r['obligation']}")
        print(f"                authority: {r['authority']}")
        for ev in r["evidence"]:
            print(f"                  - {ev}")
        print(f"                -> {r['note']}\n")
    print(f"URGENT (exemption-fatal, not yet satisfied): {len(urgent)} -> " + ", ".join(r["id"] for r in urgent))
    print("\nThis panel assembles and flags. It never concludes. Counsel opines.")


if __name__ == "__main__":
    main()
