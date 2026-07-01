# Authority Model (design)

Companion to [product-thesis.md](product-thesis.md). Pressure-tests the source-of-truth layer.
The premise: every load-bearing claim traces to an authoritative source or a named human
authority. This doc designs the *model*, not a source list.

> Status: v0.7 (2026-06-30). Captured from an architecture pressure-test. Refine per the
> thesis Self-Refinement Protocol.

## The core correction

The spine was missing **structure**, not sources. "Authority" was a citation *string* on a
control; a string cannot carry conflict resolution, drift, or provenance. Authority must be a
**typed node** in a graph, and provenance must be an **edge** (control -> authority node with a
`pinned_version`), so change propagates.

## Four axes on every authority node

1. **Tier** - can it *independently* support a load-bearing legal claim?
2. **Sovereign** - Federal-SEC | FINRA (SRO) | State (blue-sky, ×50) | Money-transmission | Corporate. *The axis the original spine lacked.*
3. **Function** - generates controls | provides evidence | emits drift events | gives context (usually exactly one).
4. **Volatility** - static-once-captured vs continuously-monitored, with a pinned version.

## The load-bearing rule

Only three classes can *independently* carry a legal conclusion:
**(A) binding primary law, (B) a parallel sovereign's binding law, (C) a named attorney
opinion.** Everything else is evidence, interpretation, or context. Interpretive guidance
carries *operational expectation*, never the legal conclusion.

## Tiers

- **A. Binding primary law** (load-bearing; generates controls; multi-sovereign ROOTS):
  SEC statutes; SEC rules (CFR/eCFR); SEC releases + **exemptive/orders** (binding law the CFR
  diff misses - Apr-2026 proof); SEC forms (schema + obligation); FINRA Rulebook + Funding
  Portal Rules (binding on members); State blue-sky ×50; Money-transmission/FinCEN (if funds
  touched); State corporate law (valid issuance).
- **B. Interpretive authority** (NOT independently load-bearing; an EDGE on the rule it
  interprets): C&DIs; SEC staff guidance; FINRA Regulatory Notices (a notice *implementing* a
  rule inherits weight); FINRA Manual; SEC **no-action letters** (fact-gated, revocable -> the
  fact-match is itself an escalate).
- **C. Adjudicative / empirical** (outcome data; drift + status; the engine): SEC enforcement /
  AP / litigation releases; FINRA enforcement (AWCs); Federal Register (drift sensor + canonical
  text); eCFR (codified-law drift backbone).
- **D. Operational / evidentiary** (operative facts; evidence): transfer-agent records; funding
  portal ops rules / prohibited conduct (binding part via FINRA; ToS contractual); issuer
  disclosures (PPM/Form C - evidence + consistency-drift vs Form D).
- **E. Named human authority** (terminal): attorney opinions - load-bearing *by designation*;
  the only node that converts `escalate` -> `satisfied-by-counsel`; provenance-stamped (attorney,
  date, scope, assumptions); **DECAYS** when a dependency drifts.
- **F. Meta / self-referential**: internal architecture & design assumptions - not legal, but
  load-bearing for *system correctness*; monitored like any authority (the Form-D-XSLT gotcha,
  substring bad-actor matching, the 180-day integration window); emits *internal* drift events.

## Conflict handling (detect; resolve only the mechanical cases; escalate the rest)

- **Hierarchical (same sovereign):** lex superior (statute > rule > release; Commission > staff)
  + lex posterior (newer > older) -> auto-resolvable, show the work.
- **Cumulative (different sovereigns):** Federal + FINRA + State + MTL are a *set to satisfy*,
  not a conflict. Union the obligations; never let one sovereign "win." (Why multi-sovereign
  must be modeled: most "conflicts" are cumulative duties a single-sovereign spine silently drops.)
  *Corollary (intentional, not a bug):* one upstream fact can legitimately escalate several
  controls across several sovereigns - e.g. a funding-portal `CFPORTAL-W` withdrawal flags
  `portal_finra_member` (FINRA), `funds_qualified_third_party` (money-transmission), and
  `portal_prohibited_conduct` (FINRA conduct) at once. That is the cumulative model working: each
  sovereign's obligation genuinely fails, and counsel must address each. The controls cross-reference
  the shared root in their evidence ("see funds_qualified_third_party / portal_finra_member") rather
  than collapsing the count - we surface the coupling, we don't hide a real multi-sovereign failure
  behind a dedup.
- **Genuine interpretive tension:** a C&DI narrows a rule; a no-action letter cuts against text
  -> NEVER auto-resolved -> `escalate_to_counsel` with both authorities surfaced and the tension
  named.

## Drift (one mechanism)

Every node has `pinned_version`; every control and opinion has dependency edges. **Drift = a
node's version changed since pinning -> stale-flag propagates to dependents.** Unifies: eCFR
amendment, new release/order (Fed Reg), C&DI update, new enforcement order (bad-actor), withdrawn
no-action letter, new issuer filing (fact drift), PPM-vs-Form-D mismatch, and a counsel opinion
staling because a relied-on rule moved. Static nodes (historical orders, filed docs, statutes)
are pinned but polled rarely.

## The smallest clean model

Irreducible spine = **four nodes**: (1) Federal securities primary (statute -> CFR -> release/order),
(2) the adjudicative feed (SEC + FINRA enforcement) = drift + bad-actor, (3) the named-counsel
terminal node (scope/assumptions/decay), (4) the system-assumption meta-node. Everything else is
added **per product surface** (funding portal -> add FINRA + money-transmission; 50-state retail ->
add blue-sky); interpretive guidance + operational docs attach as edges/evidence, never as new roots.

## Critique of the current architecture

1. **Single-sovereign blind spot (biggest):** spine assumes Federal-SEC is the world; real
   offerings are multi-sovereign. Without the sovereign axis the system silently under-covers and
   *looks* complete - the worst failure mode for a counsel-ready tool.
2. **"Binding" conflated with "codified":** exemptive orders / releases / FINRA member rules are
   binding and often not in the CFR; mis-tiering them as interpretive loses real obligations.
3. **Interpretive guidance mis-modeled:** as "context" it drops conditions; as "law" it overclaims.
   Fix = edge-not-root (guidance annotates the obligation).
4. **Human-authority node under-built:** the thesis hinges on counsel opining, yet "attorney
   opinion" is a line item. Must be the terminal, provenance-stamped, decaying node or the record
   silently rots.
5. **No model of the system's own fallibility:** evaluators encode assumptions that, if wrong,
   silently flip control states. The source-of-truth layer must include truths about itself.

**Reframe of the 90% claim:** the automatable fraction is bounded by public-vs-private *locus*,
not by authority. For 506(b) much of the surface is private. Honest version: "assemble 90% of the
*automatable* surface and crisply delineate the rest as private/counsel." Implication: 506(c)
(verification-documented) and Reg A (public qualification) automate *more* than 506(b) and may be
the better wedge.

## Implementation status

- **Sovereign axis:** implemented (v0.8) - controls carry `sovereign`; panel self-reports coverage gaps.
- **Provenance-as-edge + drift:** implemented (v0.9) - `controls/authorities.json` registry (nodes
  with `pinned_version`); controls cite by `authority_refs`; `scripts/authority-drift.py` checks
  eCFR-sourced nodes and propagates stale-flags to dependent controls. eCFR is auto-checkable today;
  Federal Register (releases/orders), C&DIs, FINRA, and state remain `manual` version_source (no
  automated checker wired yet).
- **Named-counsel terminal node:** implemented (v0.10) - `scripts/counsel.py` + `opinions/*.json`.
  A fresh opinion closes controls to `satisfied_by_counsel` (attributed to a named attorney/date);
  it decays on law-drift (cited authority pinned_version moved) or fact-drift (relied-on filing
  superseded), reverting to escalate.
- **Federal Register drift source:** implemented (v0.11) - `scripts/fedreg-watch.py` maps new SEC
  FR documents to authority nodes by CFR part (AFFECTS-NODES / OTHER-SEC-RULE / UNMAPPED-REVIEW),
  catching binding-but-uncodified actions (orders) that the eCFR diff misses.
- **System-assumption meta-node:** implemented (v0.12) - `controls/assumptions.json` +
  `scripts/assumption-check.py`. Verifiable assumptions are checked against live data; a VIOLATED
  check flags the controls it could corrupt; accepted limitations are surfaced on dependent
  controls in the panel. **All six tiers are now implemented.** Extended (v0.7, holistic-audit
  follow-up) to cover the Form C driver of the whole funding-portal framework: `asm-formc-raw-xml`
  + `asm-formc-fields` (verifiable, live-checked) close the gap where the framework's driving filing
  was the one input with no self-check; `asm-formc-filing-timing` (accepted) registers the
  cf_form_c_filed existence-only limitation as a first-class caveat. Registry: 17 nodes.
- **Funding-portal surface live (multi-sovereign proof):** implemented (v0.14) - `controls/reg-cf-funding-portal.json`
  now declares `driver: form_c` and evaluates against a real Form C via `edgar_formd.load_form_c` +
  `control-panel.py`'s driver dispatch. This is the first surface that exercises the **FINRA** and
  **money-transmission** sovereigns end-to-end (0 coverage gaps), confirming the cumulative-duties
  model (§"Conflict handling") is real: a single Reg CF raise is satisfied only by the union of
  Federal-SEC + FINRA + money-transmission + state legs, not by any one sovereign. Public-side legs
  (Form C on file, the $5M cap, the named intermediary by CIK/CRD/`007-` file number, signature
  persons → bad-actor screen) compute from EDGAR; the FINRA-conduct/fund-custody/state legs stay
  private/runnable and resolve to open/escalate.
- **FINRA membership auto-verified (first verified FINRA-sovereign control):** implemented (v0.15) -
  `scripts/finra-portal-check.py` resolves `portal_finra_member` from two authoritative public
  registers joined on the SEC file number: SEC registration (EDGAR `CFPORTAL` form family, incl.
  `CFPORTAL-W` withdrawal detection) + FINRA membership (the "Funding Portals We Regulate" list,
  directly fetchable HTML). `satisfied` only when both confirm with reconciling names (a pure
  public-register fact); `escalate` on withdrawal / inconsistency / name mismatch; `open` if
  unreachable. Registered as system-assumption nodes (`asm-cfportal-forms`, `asm-finra-fp-html`).
- **Money-transmission leg evidenced (first verified money-transmission-sovereign control):**
  implemented (v0.16) - `scripts/fund-custody-check.py` evidences `funds_qualified_third_party`
  from public EDGAR data: the portal's Form Funding Portal (`CFPORTAL`) discloses the investor-funds
  custodian (structured `escrowArrangements/investorFundsContacts`), the check confirms it is a third
  party distinct from the portal (portal-holds-funds → escalate), and confirms it is a registered
  broker-dealer via `X-17A-5` FOCUS filings (a qualified third party under 227.303(e)(1), MTL/MSB-
  exempt). `open` when the structure holds (executed agreement + AML stay private), `escalate` on
  portal-holds-funds. Registered as `asm-cfportal-escrow-fields`.
- **Portal prohibited-conduct evidenced (FP Rule 200):** implemented (v0.17) - the `portal_conduct`
  evaluator reuses the portal's Form Funding Portal to cross-reference the funds-handling prong and
  scan the structured criminal/regulatory/civil/financial disclosure answers (affirmative → escalate).
  Notable as a never-opine boundary case: it surfaces the portal's disclosed compensation but refuses
  to flag it, because transaction-based comp / a financial interest is permitted to portals
  (227.205/300(c)) - the system declines a conclusion the surface facts invite but the law forbids it
  to draw.
- **Not yet built (automated drift sources only):** FINRA *rulebook/notices* (the FP Rule text
  itself), state blue-sky, and money-transmission *rule-text* drift remain `manual` version_source
  (no automated drift checker) - distinct from the membership *register*, fund-custody *disclosure*,
  and portal-conduct *disclosure* checks above, which are now live.

## Revision Log
- **v0.7 (2026-06-30):** Consolidation freeze of the funding-portal set: a holistic (whole-artifact,
  not per-diff) audit found the framework's Form C driver had no Tier-F self-check while Form D did;
  added `asm-formc-raw-xml` / `asm-formc-fields` (live-checked) + `asm-formc-filing-timing` (accepted),
  and documented the multi-sovereign shared-cause escalation as intentional (cumulative duties).
- **v0.6 (2026-06-30):** Portal prohibited-conduct evidenced from the Form Funding Portal
  (funds-handling cross-ref + FP Rule 200 disclosure scan), with a never-opine boundary case:
  compensation surfaced, not flagged (transaction-based comp is permitted to portals).
- **v0.5 (2026-06-30):** Money-transmission leg evidenced — `funds_qualified_third_party` is the
  first money-transmission-sovereign control to reach an evidenced state, from the portal's Form
  Funding Portal escrow disclosure + the custodian's broker-dealer (X-17A-5) registration. All three
  non-issuer CF sovereigns (federal-SEC, FINRA, money-transmission) now have public-side automation.
- **v0.4 (2026-06-30):** FINRA membership auto-verified — `portal_finra_member` is the first
  FINRA-sovereign control to reach a verified state, from the SEC (EDGAR CFPORTAL) + FINRA
  registers joined on the SEC file number.
- **v0.3 (2026-06-30):** Funding-portal surface (Form C driver) marked live — first end-to-end
  exercise of the FINRA + money-transmission sovereigns; confirms the cumulative-duties model.
- **v0.2 (2026-06-29):** Marked sovereign axis + provenance/drift as implemented; noted remaining gaps.
- **v0.1 (2026-06-29):** Initial authority-model design from the architecture pressure-test.
