# Authority Model (design)

Companion to [product-thesis.md](product-thesis.md). Pressure-tests the source-of-truth layer.
The premise: every load-bearing claim traces to an authoritative source or a named human
authority. This doc designs the *model*, not a source list.

> Status: v0.1 (2026-06-29). Captured from an architecture pressure-test. Refine per the
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
- **Not yet built:** the named-counsel terminal node (opinion-of-record with decay); the
  system-assumption meta-node as data; FINRA/state/MTL automated drift sources.

## Revision Log
- **v0.2 (2026-06-29):** Marked sovereign axis + provenance/drift as implemented; noted remaining gaps.
- **v0.1 (2026-06-29):** Initial authority-model design from the architecture pressure-test.
