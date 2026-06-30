# Product Thesis (living document)

**One line:** The "counsel-ready, drift-monitored" compliance layer for securities offerings.
Vanta-for-securities-counsel. The product makes an issuer *counsel-ready* and monitors for
*drift*; the lawyer still opines. It assembles and flags. **It never opines.**

> Status: v0.2 (2026-06-29). This is THE goal this repo serves, not a side note. It is a
> living document, meant to be **constantly refined**. See the Self-Refinement Protocol
> directly below. Keep it honest: mark what's conviction vs. open question.

---

## Self-Refinement Protocol (how this doc improves without being asked)

This is the standing instruction, modeled on the repo's Operating Principles (capture the
fix; the goal steers the work). **Any session that does substantive work touching this
repo must, without waiting to be prompted:**

1. **Read this doc first** when the work is product-relevant (CLAUDE.md points here).
2. **Fold new understanding back in proactively.** If research, a data pull, a user remark,
   or an implementation detail sharpens, contradicts, or answers anything here - update the
   relevant section, move items between "open" and "resolved," and **bump the Revision Log**.
   Do this as part of the work, not as a separate chore the user has to request.
3. **Point the research at the open questions.** The autoresearch loop's backlog should be
   derived from this doc's Open Questions and the control-set it needs (bad-actor §506(d),
   §502 conditions, blue-sky, accreditation verification, precedent mining). The loop exists
   to *retire open questions here*, so each pass should generate the next refinement.
4. **Stay honest about confidence.** Tag conviction vs. hypothesis vs. open. Never let the
   doc drift into wishful certainty - same discipline the wiki uses.

> The honest boundary (Operating Principle #3, applied to myself): I do not think between
> sessions. "Without prompting" works because this instruction lives in always-loaded memory
> and future sessions reload it - the persistence is external, not autonomous cognition. It
> fires in sessions that load this repo's memory; merging to `main` makes it canonical
> everywhere. That is the mechanism, stated plainly.

## The positioning (why this is the defensible spot)

Most "AI for law" tries to **replace the authority** (be the lawyer, give the opinion). That
is the malpractice trap and where these products die. This product builds the **layer
underneath the authority**:

- **Vanta** does not replace the auditor. It makes you continuously audit-ready and
  monitored; the CPA still signs.
- **This product** does not replace counsel. It makes you continuously counsel-ready and
  drift-monitored; the lawyer still opines.

The author is the issuer. The authority is counsel. We are the substrate they both stand on.

## The non-negotiable discipline (this is the whole moat's foundation)

A question/output in this system **never resolves to a legal conclusion.** It resolves to one
of three states:

- `satisfied + evidence attached`
- `open`
- `escalate to counsel` (a genuine facts-and-circumstances judgment call)

Never "✅ Compliant" or "Yes, 506(c) is available." Always "9/11 controls evidenced · 2 open ·
1 needs counsel," each with a rule citation and the evidence behind it. The conclusion is
always counsel's. The moment our UI reads as a conclusion, we've stepped into the lawyer's
chair and lost the defensible position.

## The four loops (Vanta's skeleton, securities edition)

1. **Requirement map** - decompose an offering type into a control checklist with rule
   citations (e.g., 506(c) -> accredited verification on every purchaser, Form D in 15 days,
   no Rule 506(d) bad actor, state notice filings, integration analysis). The SEC wiki in
   this repo IS this layer.
2. **Gap check** - current state vs. the map; readiness %. Reconcile the **Form D on EDGAR**
   against the cap table and the PPM. Disclosure-consistency across documents.
3. **Drift monitor** (the subscription engine - a lawyer checks once at closing, we check
   continuously):
   - Exemption drift (506(b) + a public solicitation act blows the exemption)
   - Threshold drift (non-accredited count >35; raise approaching Reg CF $5M / Reg A $75M)
   - Bad-actor drift (Rule 506(d): a new SEC/state order against an officer/director/20%
     holder silently disqualifies the exemption)
   - Deadline drift (Form D 15 days, Form C-AR annual, Reg A ongoing, state blue-sky)
   - Regulatory drift (a rule a *live deal* depends on changed - our autoresearch machine)
4. **Counsel-ready record** - assemble the exemption-analysis memo skeleton: every control,
   its evidence, its citation, open judgment calls flagged. Counsel opines on the residual
   ~10% instead of building the 90%. That billable-hour compression is the sale.

## Architecture (v0.2 - the control model, axes, and drift engine)

### The atom: a Control

A control is one atomic, citable, testable, owned obligation. The count per offering is an
**output of the rule text**, not a choice: for 506(b), decompose 17 CFR 230.501 / 230.502(a-d)
/ 230.503 / 230.506(b)(d)(e) into ~12-18 atoms. (The 8-row demo collapsed several.)

```
Control {
  id
  offering_type            # e.g., "506(b)"
  obligation               # one atomic duty, plain language
  authority {              # POLYMORPHIC - see drift layer C
    type                   # CFR_section | FR_document | release | CDI | no_action_letter
    citation               # e.g., "17 CFR 230.502(c)"
    pinned_version         # eCFR amendment_date or text_hash | FR doc number | release no.
  }
  state                    # satisfied | open | runnable | escalate_to_counsel | n/a
  locus                    # public | private | hybrid
  owner                    # issuer | counsel | system | third_party
  cadence                  # point_in_time | continuous
  severity                 # exemption_fatal | curable_procedural | informational
  evidence[]               # pointers (Form D accession, verification record, board consent)
  drift_conditions[]       # the change(s) that flip this control's state
  last_verified
}
```

### The five axes (a gap is a matrix, not a list)

"Open" is meaningless until tagged. Each control carries all five; useful views are slices:

| Axis | Values | Example slice |
|---|---|---|
| State | satisfied / open / runnable / escalate / n/a | "what still needs evidence?" |
| Locus | public / private / hybrid | "what can we auto-check vs. must the issuer give us?" |
| Owner | issuer / counsel / system / third_party | "what's on the founder's plate this week?" |
| Cadence | point_in_time / continuous | "what do we monitor forever?" |
| Severity | exemption_fatal / curable_procedural / informational | "what could blow the exemption?" |

The high-value default view = `exemption_fatal AND private AND point_in_time AND open` (the
issuer's urgent homework) and `continuous AND public` (what the system watches on its own).

### The three-layer drift engine (verified against live APIs 2026-06-29)

Drift has three sources, matched to where the truth lives:

- **Layer A - Private-state drift** (the *facts* change): new investor, a marketing/solicitation
  act, an officer change, raise-amount change. Source: customer integrations + uploads.
- **Layer B - Public-state drift** (the *world* changes around a fixed fact): a related person
  gets a new SEC order (506(d) bad-actor drift); a conflicting nearby offering appears; Form D
  reconciliation. Source: EDGAR + enforcement/admin-proceeding polling (`sec-fetch.sh`,
  data.sec.gov, getcurrent feeds).
- **Layer C - Regulatory drift** (the *rule itself* moves). Pin each control to its authority +
  version; diff on a schedule; any change -> flag every citing control **stale -> re-verify ->
  escalate to counsel** (NEVER "now non-compliant"). Verified endpoints:
  - **eCFR versioner** - per-section amendment dates:
    `GET https://www.ecfr.gov/api/versioner/v1/versions/title-17.json?part=230`
    (confirmed: §230.506 amendment history `2016-11-21 / 2021-01-14 / 2021-03-15 / 2021-06-09`).
    Pin `{citation, amendment_date, text_hash}`; a new date -> stale flag. ("git for the
    control's legal basis.")
  - **Federal Register API** - the SEC rulemaking pipeline (early warning before codification):
    `GET https://www.federalregister.gov/api/v1/documents.json?conditions[agencies][]=securities-and-exchange-commission&conditions[type][]=RULE`
    (confirmed: 1,020 SEC final rules; surfaced the FDTA final rule).
  - **Autoresearch loop** - the SOFT-LAW watcher. **Critical caveat, with live proof:** a pure
    CFR diff MISSES non-codified authority. The April 2026 tender-offer change came via an
    **exemptive order**, not a CFR amendment; C&DIs, no-action letters, and staff guidance never
    touch the CFR. So `authority.type` must be polymorphic and each type gets its own watcher;
    the autoresearch loop covers orders/guidance/no-action (it already caught that April order).

### Verified data sources for the bad-actor moat (2026-06-29 probe)

De-risked before building. Findings:

- **Continuous drift leg = GREEN.** The official **SEC Administrative Proceedings RSS feed**
  (`https://www.sec.gov/rss/litigation/admin.xml`) returns live, structured RSS (confirmed:
  25 items, same-day, real respondent names). Free, official, pollable -> this is the
  continuous bad-actor / enforcement drift signal. (Litigation-releases feed exists too; the
  guessed URL 404'd, find the current one.)
- **Historical point-in-time check (SALI) = YELLOW.** The SEC Action Lookup - Individuals
  (`/litigations/sec-action-look-up?last_name=...`) is the right *official* dataset (court
  judgments + admin orders, individuals named in SEC actions) BUT its results render
  **client-side via Drupal Views AJAX** - no clean GET-JSON (`?_format=json` -> 406). Options
  to query it: (a) drive it with the pre-installed **Playwright/Chromium**, (b) rebuild a
  back-index from the `/files/litigation/admin|litreleases` archives, or (c) a paid
  third-party enforcement API. Not blocked; just not a one-liner.
- **Build-order implication:** build the slice on the GREEN leg first (continuous monitor on
  the AP RSS) - it works on free official data today AND is the subscription value. Treat the
  historical SALI lookup as v2 (Playwright).

## The moat questions (public data answers these; a solo human cannot)

- **Bad-actor + rule-change monitoring** - continuous, data-grounded, across a whole client
  book. Grounded in SEC enforcement / administrative-proceeding data + the rule corpus.
- **Precedent benchmarking** - mine *qualified/accepted* filings on EDGAR so an issuer's
  draft is already "market" before counsel sees it ("here's what good looks like").

## Data boundaries (be honest about what we can and can't ground)

- **Public / EDGAR (we have direct access via `scripts/sec-fetch.sh` + data.sec.gov):**
  Form D verification, precedent disclosure mining, bad-actor lookups (enforcement data),
  rule-change monitoring, the rule corpus.
- **Private / internal (customer must provide; not on EDGAR):** cap table, subscription docs,
  accreditation-verification records, board consents, the PPM/deck. Most "counsel-ready"
  evidence is here. The product's integrations live here.
- **Out of scope (don't let the system answer these - they're conclusions or unknowable):**
  "Are we compliant?" (conclusion), "is the exemption available?" (legal conclusion),
  management intent, anything forward-looking.

## How this connects to what's already built in this repo

- The **SEC/EDGAR wiki** (~87 pages, cited, lint-clean) = the **controls framework** / rule
  model. Each concept page (Reg D, Reg A, Rule 144, bad-actor disqualification, Form D, etc.)
  is a candidate control definition.
- **`scripts/sec-fetch.sh` + data.sec.gov** = the **verification / monitoring / precedent**
  layer.
- The **autoresearch loop** = the **regulatory-drift monitor** prototype (it already caught
  the Apr 2026 tender-offer change and the climate-rule rescission).

## Open questions to refine (the point of this being a living doc)

**Resolved in v0.2:**
- ~~Control data model~~ -> defined (the Control atom + five axes).
- ~~Rule-change-monitor mechanism~~ -> defined + endpoints verified (eCFR versioner + Federal
  Register API + autoresearch for soft law; codified-only diff is insufficient).

**Still open:**
- ICP: who is the first buyer - the issuer (founder/CFO) or the law firm itself (a tool that
  makes associates faster)? Different products.
- Wedge offering type: start with Reg D 506(c) (cleanest, highest volume, verification-heavy)?
- Build vs. partner for accreditation verification.
- How to source/normalize the private evidence (integrations vs. upload).
- What's the minimum defensible "counsel-ready package" a lawyer will actually accept?
- Control-set authoring: hand-curate from the wiki, or auto-generate atoms from CFR text then
  human-review? (Likely the latter, with counsel sign-off on the template.)
- Bad-actor matching: how to disambiguate a name hit against enforcement data to an acceptable
  false-positive rate (this is itself an "escalate to counsel," never an auto-conclusion).

## Revision Log

- **v0.15 (2026-06-30):** Auto-verified **FINRA membership** — `portal_finra_member` goes from
  "runnable; not yet wired" to a live, deterministic two-register check (`scripts/finra-portal-check.py`).
  It joins the SEC register (EDGAR `CFPORTAL` form family — registered iff a CFPORTAL exists and the
  latest isn't a `-W` withdrawal) and the FINRA register (the "Funding Portals We Regulate" list,
  whose own words are "registered with the SEC as funding portals **and are funding portal members
  of FINRA**") on the **SEC file number** (Form C's `007-00042` → FINRA's `7-42`). Resolves to
  `satisfied` only when both registers confirm with reconciling legal names — a *pure public-register
  fact*, the kind the thesis says is the automatable core — and to `escalate` on withdrawal, register
  inconsistency, or name mismatch; `open` if a source is unreachable (never a silent clearance). This
  is the **first FINRA-sovereign control to reach a verified state**, and it deterministically ties the
  Form C brand name ("Mr. Crowd") to the legal filer ("Ksdaq Inc."), which is itself a useful
  disambiguation the issuer's own filing doesn't make explicit. Diagnose-before-detour paid off twice:
  the FINRA page looked like it needed a JS render / had no API, but a plain `curl` returns parseable
  HTML (200), and the file-number key beats fuzzy name matching. Captured the method in `CLAUDE.md`,
  registered the new dependencies as system-assumption nodes (`asm-cfportal-forms`, `asm-finra-fp-html`
  — both live-checked and holding; `asm-fileno-normalize` accepted, fails safe to escalate), and added
  hermetic branch tests (`tests/test_finra_portal.py`). `make test` green (12 suites). Sharpens the
  "more-automatable surfaces are the wedge" claim: Reg CF's registration legs are *fully* public, so
  they automate to a verified state where 506(b)'s defining duties cannot.
- **v0.14 (2026-06-30):** Shipped the **Form C driver** — the funding-portal surface goes from
  stub to live. `scripts/edgar_formd.py` now drives BOTH Form D and Form C (`load_form_c` /
  `parse_form_c`, identical envelope shape), and `control-panel.py` dispatches on a framework's
  new `driver` field. `controls/reg-cf-funding-portal.json` now evaluates against a real Form C:
  the public-side legs compute (Form C existence on EDGAR → `cf_form_c_filed`, kept `open` not
  `satisfied` because the obligation is multi-part — filed *before commencement* + annual C-AR —
  and only existence is a verified public fact, mirroring the Form D `form_d_filed` precedent;
  offering max vs the $5M **rolling 12-month** Reg CF cap → `open`, because an aggregate can't be
  concluded from one filing; the single named intermediary by CIK + CRD + `007-` funding-portal
  file number → feeds the FINRA-membership check; signature persons → the 227.503 bad-actor
  screen), while FINRA-conduct, fund-custody, and state legs resolve to `open`/`escalate`. The
  panel draws 0 legal conclusions (control states are evidence-states, never "compliant"). This is the first time the **FINRA**
  and **money-transmission** sovereigns are exercised end-to-end (0 coverage gaps), proving the
  multi-sovereign authority model is real and not Federal-SEC-only. Confirms the "better wedge"
  reasoning from another angle: like 506(c)'s documentable verification, Reg CF's surface is
  unusually public (the intermediary, cap, and filing are all on EDGAR), so more of it automates
  cleanly. Verified live on CIK 2140631 (20Slash20, Inc. via Mr. Crowd); Form D path
  regression-clean; `make test` green (a new hermetic `tests/test_edgar_formc.py` feeds canned
  Form C XML through the parser + every CF evaluator, asserting the never-opine invariant offline).
  Gotcha captured (Form C `primaryDocument` = `xslC_X01/primary_doc.xml`, raw XML is the
  prefix-stripped sibling) in code + CHANGELOG. **The pre-commit verifier earned its keep here:**
  it flagged that the first cut marked `cf_form_c_filed` `satisfied` on a multi-part exemption-fatal
  obligation when only one leg was verified — a quiet never-opine softening — which was corrected to
  `open` before the work settled. That is the assemble-don't-opine discipline catching itself.
- **v0.13 (2026-06-29):** Added the **506(c)** control set (`controls/reg-d-506c.json`, 15 controls)
  - the framework now carries a SECOND offering type, proving it's a platform, not one checklist.
  506(c) flips the constraints: general solicitation permitted, but ALL purchasers accredited and
  the issuer must take **reasonable steps to verify** (the documentable duty). Two new evaluators
  (`exemption_is_506c`, `all_accredited_506c`) auto-compute from Form D. Verified live on a real
  506(c) filer (CIK 2085470): exemption + all-accredited satisfied from public data; the two
  verification controls surface as the new exemption-fatal items. Reuses the existing authority
  registry/sovereign/drift/counsel/assumption machinery unchanged. Supports the "better wedge"
  thesis: 506(c) verification is private but **documentable** (vs 506(b)'s unverifiable
  no-solicitation), so more of its surface is automatable. `make test` green.
- **v0.12 (2026-06-29):** Built the **system-assumption meta-node** (authority-model Tier F) -
  the last tier; the model's six tiers are now all implemented. `controls/assumptions.json`
  registers the truths the evaluators rely on: **verifiable** assumptions (executable checks -
  Form D raw-XML location, field localnames, the '06b' code, eCFR/Federal-Register/AP-RSS shapes)
  and **accepted** ones (known limitations/heuristics - substring bad-actor matching, the AP
  rolling-window, the 180-day integration proxy). `scripts/assumption-check.py` runs the
  verifiable checks against live data (6/6 hold) and, on a VIOLATED check, flags the controls that
  assumption could silently corrupt. `control-panel.py` surfaces the accepted limitations on the
  controls that rely on them. This is the "truths about itself" layer that guards the automated
  surface from being confidently wrong. `make test` green.
- **v0.11 (2026-06-29):** Wired the **Federal Register drift source** (`scripts/fedreg-watch.py`),
  closing the "binding != codified" gap that a pure eCFR diff misses. Queries the FR API for SEC
  documents since a date and maps them to authority nodes by CFR part: touches a part we cite ->
  AFFECTS-NODES (lists dependent controls for review); touches title 17 but not our parts ->
  OTHER-SEC-RULE (context); no CFR reference (e.g., an ORDER) -> UNMAPPED-REVIEW (the
  binding-but-uncodified catch - the April-2026-order class). Verified live (3 part-230 SEC rules
  flagged since our pin; 98 uncodified SEC notices surfaced for review). No-silent-caps: prints a
  truncation note past the page limit. Never concludes - "review; counsel assesses." `make test` green.
- **v0.10 (2026-06-29):** Built the **named-counsel terminal node** (the authority the thesis
  hinges on). `scripts/counsel.py` + an opinions-of-record file (`opinions/*.json`): a fresh
  opinion *closes* covered controls into `satisfied_by_counsel`, **attributed to a named
  attorney + date + opinion id** (the system still draws 0 conclusions). The opinion **decays**:
  it snapshots the authority versions + facts it relied on, and `control-panel.py --opinions`
  reverts a control to `escalate_to_counsel` ("STALE - re-opine") when a cited authority's
  pinned_version drifts (law-drift, via the registry) or the underlying Form D is superseded
  (fact-drift). Verified end-to-end (4 controls close; un-snapshotting law+fact reverts them).
  This is the piece that makes "counsel opined, and the system knows when that opinion went
  stale" actually work. `make test` green.
- **v0.9 (2026-06-29):** Implemented **provenance-as-edge + version-pinned drift** (authority
  model made real). `controls/authorities.json` is the authority REGISTRY (nodes: type,
  sovereign, citation, `pinned_version`, `version_source`); CFR sections pinned to their actual
  current eCFR amendment_dates. Controls now cite authorities by id (`authority_refs`) - the
  provenance edge - all resolving, no danglers. `scripts/authority-drift.py` checks each
  ecfr-sourced node against current eCFR and, on a version change, **propagates a stale-flag to
  every dependent control** (verified live: 0 drift now; un-pinning 230.506 flags all 4 citing
  controls `stale -> re-verify -> escalate`, never "non-compliant"). `control-panel.py` shows
  the pinned version per control (provenance on the counsel-ready record). `make test` green.
- **v0.8 (2026-06-29):** Implemented the **sovereign axis** in the control schema. Every control
  in `controls/*.json` now carries `sovereign` (federal-sec / finra / state-blue-sky /
  money-transmission / corporate) and each framework declares `sovereigns_in_scope`.
  `control-panel.py` self-reports **sovereign coverage** and flags any in-scope sovereign with
  0 controls as a COVERAGE GAP -> escalate (the anti-blind-spot mechanism: the system refuses to
  look complete when it under-covers a sovereign; verified firing). Adding the axis immediately
  exposed a real gap in our own 506(b) set - the **corporate** sovereign (valid authorization /
  issuance) had 0 controls; closed with 2 stubs. Added `controls/reg-cf-funding-portal.json`: a
  multi-sovereign STUB for the portal surface (federal-sec + finra + money-transmission +
  state-blue-sky) proving the schema generalizes. `control-panel.py` gained `--framework`.
  `make test` green.
- **v0.7 (2026-06-29):** Architecture pressure-test produced a typed AUTHORITY MODEL
  ([authority-model.md](authority-model.md)). Key sharpenings that revise this thesis:
  (1) authority is a typed graph node with provenance as an edge, not a citation string;
  (2) add a **sovereign axis** (Federal-SEC / FINRA / State blue-sky ×50 / money-transmission /
  corporate) - the original spine was single-sovereign and silently under-covers;
  (3) "binding" != "codified" (exemptive orders / releases / FINRA member rules are binding, often
  not in the CFR); (4) interpretive guidance (C&DIs, no-action, FINRA notices) is an *edge* on the
  rule it interprets, never a root; (5) the named-counsel node is the terminal, decaying authority
  and must be modeled as such; (6) the system's own design assumptions are a monitored authority
  class (system correctness). Conflict model: hierarchical=auto, cumulative=union, genuine
  tension=escalate. Drift unified as version-change propagation along edges. Honest reframe: the
  automatable fraction is bounded by public-vs-private locus, not authority -> 506(c)/Reg A may be
  the better wedge than 506(b).
- **v0.6 (2026-06-29):** Wired the `integration` control from a stub into a real public-data
  auto-check (the issuer's other EDGAR offering-type filings within a ~6-month window, via
  `edgar_formd.list_filings` + `OFFERING_FORMS`) - still never "satisfied" (integration is a
  legal judgment), but now evidenced/flagged from data. Added a self-contained **HTML
  counsel-ready report** renderer (`control-panel.py --html`): badged states, the
  exemption-fatal urgent box, a "draws no legal conclusions" banner, citations + axes per
  control. Verified live; `make test` green. This is the first artifact in the shape a lawyer
  actually consumes (Loop 4, the counsel-ready record).
- **v0.5 (2026-06-29):** Shipped the first counsel-ready CONTROL PANEL. The §506(b) control
  framework now exists as data (`controls/reg-d-506b.json`, 14 atoms derived from 17 CFR
  230.501-503 / 506(b)(d)(e), each with authority + the five axes). `scripts/control-panel.py`
  loads a CIK's Form D, auto-computes state where public data allows (exemption claimed,
  non-accredited ceiling, info-delivery N/A, bad-actor screen, amount/first-sale extraction),
  marks the rest open/private, and renders the whole checklist with an "exemption-fatal, not
  yet satisfied" urgent view - never-opine throughout. Shared Form D logic factored into
  `scripts/edgar_formd.py` (screen-offering.py refactored onto it; `make test` still green).
  Partially resolves the "control-set authoring" open question: framework-as-data, with
  evaluators filling state - counsel still owns the template sign-off.
- **v0.4 (2026-06-29):** Shipped the first END-TO-END flow `scripts/screen-offering.py`:
  CIK -> latest Form D -> issuer + related persons (506(d) covered persons, with roles) ->
  bad-actor drift screen, never-opine output. Verified live on a real Form D (3 covered
  persons extracted with relationships). Lesson captured: EDGAR submissions' `primaryDocument`
  for Form D points at the XSLT-rendered HTML (`xslFormDX08/primary_doc.xml`); the raw
  structured XML is the same filename without the styling-dir prefix.
- **v0.3 (2026-06-29):** De-risked the bad-actor moat's data foundation before building
  (Self-Refinement Protocol firing on its first real opportunity). Continuous leg GREEN (SEC
  Administrative Proceedings RSS, live + structured); historical SALI lookup YELLOW (JS-only,
  needs Playwright/archives/3rd-party). Set build order: green leg first. Shipped the first
  product atom `scripts/badactor-watch.py` (continuous monitor; never-opine output).
- **v0.2 (2026-06-29):** Added the Architecture (Control atom schema; the five axes -
  state/locus/owner/cadence/severity; the three-layer drift engine). Verified the
  rule-change-monitor endpoints live: eCFR versioner (per-section amendment dates for 17 CFR
  Part 230) and the Federal Register API (SEC rulemaking). Established the polymorphic
  `authority` field and the soft-law caveat (CFR diff alone misses exemptive orders / C&DIs /
  no-action - proven by the Apr 2026 tender-offer order). Added the Self-Refinement Protocol
  so this doc updates itself as a default behavior. Promoted the doc to "THE goal."
- **v0.1 (2026-06-29):** Initial capture from conversation. Positioning (layer underneath
  authority / Vanta-for-counsel), the never-opine discipline, four loops, moat questions,
  data boundaries. Author: issuer; authority: counsel; us: substrate.
