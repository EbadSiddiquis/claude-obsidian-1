#!/usr/bin/env python3
"""control-panel.py - render the §506(b) counsel-ready control panel for a CIK.

Reads the control framework (controls/reg-d-506b.json), loads the issuer's Form D, computes
each control's state from public data where possible, marks the rest honestly, and renders the
whole checklist (text or self-contained HTML).

THE DISCIPLINE: assembles and flags; never concludes. Each control resolves to
satisfied / open / escalate_to_counsel / n/a with a citation and a note. Counsel opines.

USAGE
  export SEC_CONTACT_EMAIL="you@example.com"
  python3 scripts/control-panel.py --cik 2141182
  python3 scripts/control-panel.py --cik 2141182 --json
  python3 scripts/control-panel.py --cik 2141182 --html /tmp/panel.html
"""
import argparse
import datetime
import html
import json
import os
import subprocess
import sys

import assumption_registry as asm_reg
import authority_registry as areg
import counsel
import edgar_formd as efd

HERE = os.path.dirname(os.path.abspath(__file__))
CONTROLS = os.path.join(os.path.dirname(HERE), "controls", "reg-d-506b.json")
INTEGRATION_WINDOW_DAYS = 180


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

    if key == "exemption_is_506c":
        ex = fd.get("exemptions") or []
        if "06c" in ex:
            return "satisfied", [f"Form D federalExemptionsExclusions = {ex}"], "Form D claims Rule 506(c) [06c]."
        if "06b" in ex:
            return "escalate_to_counsel", [f"Form D = {ex}"], "Form D claims 506(b), not 506(c) - wrong control set? Confirm with counsel."
        return "open", [f"Form D = {ex}"], "Rule 506(c) not clearly claimed on Form D; confirm the exemption relied upon."

    if key == "all_accredited_506c":
        na = fd.get("has_non_accredited")
        if na is False:
            return "satisfied", ["Form D: hasNonAccreditedInvestors = false"], "Form D reports 0 non-accredited purchasers, consistent with 506(c)'s all-accredited requirement (counsel confirms reliance)."
        if na is True:
            return "escalate_to_counsel", ["Form D: hasNonAccreditedInvestors = true"], "Form D reports non-accredited purchasers - INCOMPATIBLE with 506(c) (all purchasers must be accredited). Counsel assesses."
        return "open", [], "Non-accredited status not determinable from Form D; confirm all purchasers accredited (private)."

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

    if key == "integration_window":
        fdate = fd.get("filing_date")
        others = []
        if fdate:
            try:
                d0 = datetime.date.fromisoformat(fdate)
            except ValueError:
                d0 = None
            for f in fd.get("all_filings", []):
                if f["accession"] == fd.get("accession") or f["form"] not in efd.OFFERING_FORMS:
                    continue
                try:
                    if d0 and abs((datetime.date.fromisoformat(f["date"]) - d0).days) <= INTEGRATION_WINDOW_DAYS:
                        others.append(f)
                except ValueError:
                    continue
        if others:
            ev = [f"{f['date']} {f['form']} ({f['accession']})" for f in others]
            return "escalate_to_counsel", ev, "Other EDGAR offering filing(s) within ~6 months - assess integration / Rule 152 (counsel)."
        return "open", ["no other EDGAR offering-type filings within ~6 months"], "Public-side integration window clean; private / other-raise facts still needed - counsel assesses."

    if key == "form_d_filed":
        fs = fd.get("date_of_first_sale")
        return "open", [f"Form D on file: accession {fd.get('accession')} (filed {fd.get('filing_date')})", f"first-sale date: {fs}"], \
            "Form D is filed; confirm it was within 15 days of first sale (reconcile first-sale date vs filing date)."

    if key == "amount_reconciliation":
        ev = [f"Form D offered: {fd.get('total_offering_amount')}", f"sold: {fd.get('total_sold')}", f"remaining: {fd.get('total_remaining')}"]
        return "open", ev, "Reconcile these Form D amounts against the cap table / subscription records (private)."

    if key == "manual_runnable":
        return "open", [], "Runnable against court-order / enforcement data; not yet wired."
    if key == "manual_continuous":
        return "open", [], "Monitor on a schedule (continuous)."
    # default: manual_private / manual_hybrid
    return "open", [], "Needs internal evidence; counsel confirms."


def sovereign_coverage(framework, rows):
    """Self-report coverage along the authority-model sovereign axis: which declared-in-scope
    sovereigns actually have controls, and which are GAPS (in scope but 0 controls = the system
    does not yet cover that sovereign -> it must say so, not look complete)."""
    in_scope = framework.get("sovereigns_in_scope", [])
    counts = {}
    for r in rows:
        counts[r.get("sovereign", "UNSPECIFIED")] = counts.get(r.get("sovereign", "UNSPECIFIED"), 0) + 1
    return {
        "in_scope": in_scope,
        "counts": counts,
        "gaps": [s for s in in_scope if counts.get(s, 0) == 0],
        "undeclared": [s for s in counts if s != "UNSPECIFIED" and in_scope and s not in in_scope],
        "missing_field": [r["id"] for r in rows if not r.get("sovereign")],
    }


def build(cik, framework_path=CONTROLS, opinions_path=None):
    framework = json.load(open(framework_path, encoding="utf-8"))
    fd = efd.load_form_d(cik)
    watchlist = [fd["issuer"]] + [p["name"] for p in fd["related_persons"]]
    ctx = {"watchlist": watchlist, "badactor": run_badactor(watchlist)}
    registry = areg.load_registry()
    assumptions = asm_reg.load_assumptions()
    rows = []
    for c in framework["controls"]:
        state, evidence, note = evaluate(c, fd, ctx)
        nodes = areg.resolve(c.get("authority_refs"), registry)
        caveats = [a["statement"] for a in asm_reg.for_control(assumptions, c["id"]) if a["kind"] == "accepted"]
        rows.append({**c, "state": state, "evidence": evidence, "note": note, "authority_nodes": nodes, "caveats": caveats})
    # Named-counsel terminal node: a fresh opinion closes a control (satisfied_by_counsel); a
    # stale one (law/fact drift) reverts it to escalate. Applied BEFORE counts/urgent.
    if opinions_path:
        counsel.apply_opinions(rows, counsel.load_opinions(opinions_path), registry,
                               {"form_d_accession": fd.get("accession")})
    counts = {}
    for r in rows:
        counts[r["state"]] = counts.get(r["state"], 0) + 1
    urgent = [r for r in rows if r["severity"] == "exemption_fatal" and r["state"] in ("open", "escalate_to_counsel")]
    coverage = sovereign_coverage(framework, rows)
    return framework, fd, rows, counts, urgent, coverage


BADGE = {"satisfied": "#1a7f37", "open": "#6e7781", "escalate_to_counsel": "#bc4c00", "n/a": "#0969da",
         "satisfied_by_counsel": "#8250df"}


def render_html(framework, fd, rows, counts, urgent, coverage, cik):
    e = html.escape
    cov_items = []
    for s in coverage["in_scope"]:
        n = coverage["counts"].get(s, 0)
        if n == 0:
            cov_items.append(f'<li><b style="color:#bc4c00">{e(s)}: COVERAGE GAP</b> &mdash; in scope, 0 controls &rarr; escalate (sovereign not yet modeled)</li>')
        else:
            cov_items.append(f'<li><b>{e(s)}</b>: {n} control(s)</li>')
    for s in coverage["undeclared"]:
        cov_items.append(f'<li>{e(s)}: {coverage["counts"][s]} control(s) (not declared in scope &mdash; review)</li>')
    cov_html = (f'<div style="background:#ddf4ff;border:1px solid #54aeff66;border-radius:6px;padding:10px 14px;margin-top:12px">'
                f'<b>Sovereign coverage</b> (authority-model axis)<ul style="margin:6px 0 0">{"".join(cov_items)}</ul></div>')
    summary = " &middot; ".join(f"{e(k)}: {v}" for k, v in sorted(counts.items())) + " &middot; conclusions drawn: 0"
    trs = []
    for r in rows:
        ev = "".join(f"<li>{e(str(x))}</li>" for x in r["evidence"])
        pins = "".join(f'<div style="font-size:11px;color:#777">{e(n["id"])}@{e(n["pinned_version"])}</div>' for n in r.get("authority_nodes", []))
        opin = ""
        if r.get("opinion"):
            o = r["opinion"]
            tag = f'by counsel: {o.get("attorney")} ({o.get("date")}, {o.get("id")})'
            if not o.get("fresh"):
                tag += f' — STALE: {o.get("stale_reason")} — re-opine'
            opin = f'<div style="font-size:12px;color:#8250df;margin-top:4px">{e(tag)}</div>'
        cavs = "".join(f'<div style="font-size:11px;color:#9a6700;margin-top:2px">! known limitation: {e(c)}</div>' for c in r.get("caveats", []))
        trs.append(
            f'<tr style="border-bottom:1px solid #eaeef2">'
            f'<td><span style="background:{BADGE[r["state"]]};color:#fff;padding:2px 8px;border-radius:10px;font-size:12px;white-space:nowrap">{e(r["state"])}</span></td>'
            f'<td><b>{e(r["id"])}</b><br><span style="color:#444">{e(r["obligation"])}</span></td>'
            f'<td><code>{e(r["authority"])}</code>{pins}</td>'
            f'<td style="font-size:12px;color:#555"><b>{e(r.get("sovereign","?"))}</b><br>{e(r["severity"])}<br>{e(r["locus"])}<br>owner: {e(r["owner"])}</td>'
            f'<td style="font-size:13px"><ul style="margin:0;padding-left:16px">{ev}</ul><div style="color:#555;margin-top:4px">{e(r["note"])}</div>{opin}{cavs}</td>'
            f'</tr>')
    urgent_li = "".join(f"<li><b>{e(r['id'])}</b> &mdash; {e(r['obligation'])} <code>{e(r['authority'])}</code></li>" for r in urgent)
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Control Panel - {e(fd['issuer'])}</title></head>
<body style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:980px;margin:24px auto;color:#1f2328;padding:0 16px">
<div style="background:#fff8c5;border:1px solid #d4a72c;border-radius:6px;padding:10px 14px;font-size:13px">
<b>This is not legal advice and draws no legal conclusions.</b> It assembles evidence and flags
open items and judgment calls for counsel. Outputs are <i>satisfied / open / escalate to counsel / n/a</i>
&mdash; never &ldquo;compliant&rdquo; or &ldquo;exemption available.&rdquo; Counsel opines.</div>
<h1 style="margin:18px 0 2px">Counsel-Ready Control Panel</h1>
<div style="color:#555">{e(framework['offering_type'])} &middot; <b>{e(fd['issuer'])}</b> &middot; CIK {int(cik)} &middot; Form D {e(fd.get('accession') or '')} (filed {e(fd.get('filing_date') or '?')})</div>
<p style="font-size:14px">{summary}</p>
<div style="background:#ffebe9;border:1px solid #ff818266;border-radius:6px;padding:10px 14px">
<b>Urgent &mdash; exemption-fatal, not yet satisfied ({len(urgent)})</b>
<ul style="margin:6px 0 0">{urgent_li}</ul></div>
{cov_html}
<table style="border-collapse:collapse;width:100%;margin-top:16px;font-size:14px" border="0">
<thead><tr style="text-align:left;border-bottom:2px solid #d0d7de">
<th>State</th><th>Control</th><th>Authority</th><th>Axes</th><th>Evidence / Note</th></tr></thead>
<tbody>{"".join(trs)}</tbody></table>
<p style="color:#6e7781;font-size:12px;margin-top:18px">Generated by control-panel.py from public EDGAR + SEC data.
The bad-actor leg is a rolling-window monitor (historical SALI check pending). Private controls
require issuer evidence. This panel never concludes; counsel opines.</p>
</body></html>"""


def main():
    ap = argparse.ArgumentParser(description="Render the Rule 506(b) counsel-ready control panel for a CIK (never-opine).")
    ap.add_argument("--cik", required=True)
    ap.add_argument("--framework", default=CONTROLS, help="control framework JSON (default: reg-d-506b.json)")
    ap.add_argument("--opinions", metavar="PATH", help="opinions-of-record JSON (named-counsel node)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--html", metavar="PATH", help="write a self-contained HTML report to PATH")
    args = ap.parse_args()

    framework, fd, rows, counts, urgent, coverage = build(args.cik, args.framework, args.opinions)

    if args.html:
        with open(args.html, "w", encoding="utf-8") as fh:
            fh.write(render_html(framework, fd, rows, counts, urgent, coverage, args.cik))
        print(f"wrote {args.html}")
        return

    if args.json:
        print(json.dumps({"issuer": fd["issuer"], "cik": str(int(args.cik)), "form_d": fd.get("accession"),
                          "offering_type": framework["offering_type"], "counts": counts,
                          "sovereign_coverage": coverage,
                          "exemption_fatal_open": [r["id"] for r in urgent], "controls": rows}, indent=2))
        return

    MARK = {"satisfied": "OK ", "open": "open", "escalate_to_counsel": "FLAG->counsel", "n/a": "n/a ",
            "satisfied_by_counsel": "BY COUNSEL"}
    print(f"Counsel-ready control panel | {framework['offering_type']} | {fd['issuer']} | CIK {int(args.cik)} | Form D {fd.get('accession')}")
    print(" · ".join(f"{k}: {v}" for k, v in sorted(counts.items())) + " · conclusions drawn by the system: 0\n")
    for r in rows:
        print(f"[{MARK[r['state']]:>13}] {r['id']}  [{r.get('sovereign','?')}] ({r['severity']}, {r['locus']}, owner={r['owner']})")
        print(f"                {r['obligation']}")
        print(f"                authority: {r['authority']}")
        if r.get("authority_nodes"):
            print(f"                pinned: " + ", ".join(f"{n['id']}@{n['pinned_version']}" for n in r["authority_nodes"]))
        for ev in r["evidence"]:
            print(f"                  - {ev}")
        if r.get("opinion"):
            o = r["opinion"]
            tag = f"by counsel: {o.get('attorney')} ({o.get('date')}, {o.get('id')})"
            if not o.get("fresh"):
                tag += f"  [STALE: {o.get('stale_reason')} - re-opine]"
            print(f"                {tag}")
        for cav in r.get("caveats", []):
            print(f"                ! known system limitation: {cav}")
        print(f"                -> {r['note']}\n")
    print("Sovereign coverage (authority-model axis):")
    for s in coverage["in_scope"]:
        n = coverage["counts"].get(s, 0)
        gap = "   <- COVERAGE GAP: in scope, 0 controls -> escalate (sovereign not yet modeled)" if n == 0 else ""
        print(f"  {s}: {n} control(s){gap}")
    for s in coverage["undeclared"]:
        print(f"  {s}: {coverage['counts'][s]} control(s) (not declared in scope - review)")
    if coverage["missing_field"]:
        print(f"  ! controls missing a sovereign: {coverage['missing_field']}")
    print(f"\nURGENT (exemption-fatal, not yet satisfied): {len(urgent)} -> " + ", ".join(r["id"] for r in urgent))
    print("\nThis panel assembles and flags. It never concludes. Counsel opines.")


if __name__ == "__main__":
    main()
