# Compliance Oracle — starter scaffold

A hybrid **graph + relational** system that converts public regulatory frameworks (SEC / FINRA /
FDIC / FinCEN / eCFR / Federal Register) into citation-pinned technical specs, Written Supervisory
Procedures (WSPs), and executable system controls — for architecting a Reg CF funding portal on
sweat equity, with zero spend on legal research of public regulatory knowledge.

**The inherited invariant (from the parent project): assemble and flag, never opine.** Every
generated artifact is a CANDIDATE pending adoption by a named supervisory principal; nothing here
states a legal conclusion; attestations decay when the law drifts. The Oracle replaces the
*research and drafting* cost, not the accountable human of record.

## What's here

| File | Layer |
|---|---|
| `schema.sql` | One SQLite file, both stores: graph (`nodes`/`edges`) + relational (`controls`/`wsp_procedures`/`system_controls`/`evidence`/`attestations`/`assumptions`) |
| `ingest.py` | Fetches the **custody triad** live from eCFR (pinned amendment dates), seeds the cross-sovereign edges + an exemplar control→WSP→spec chain |
| `query.py` | The Graph-RAG traversal: control → authority bundle across sovereigns (`--json` feeds the prompt) |
| `drift.py` | Re-pins nodes against live eCFR; on a change, flags citing controls and **decays attestations** (WSP → `stale_reattest`) |
| `prompts/wsp-generation.md` | The generation prompt — hard rules that make a legal conclusion impossible to emit |

## Quickstart

```bash
export SEC_CONTACT_EMAIL="you@example.com"
python3 ingest.py                                                # build oracle.db from live eCFR
python3 query.py --control oracle_custody_qualified_third_party  # the cross-sovereign traversal
python3 query.py --control oracle_custody_qualified_third_party --json  # → paste into prompts/wsp-generation.md
python3 drift.py                                                 # the regulatory-drift monitor
```

## The seeded slice (why this one)

Investor-fund custody — the highest-risk portal function and the smallest complete
cross-sovereign example:

- **17 CFR 227.300(c) / 227.303(e)** (SEC): the portal may NOT hold investor funds; direct
  transmission to a *qualified third party* (registered BD or bank).
- **12 CFR 330.5 / 330.7** (FDIC): pass-through deposit insurance — custodial titling + records of
  actual ownership are what preserve per-investor coverage on the pooled account.
- **31 CFR 1023.210** (FinCEN): the BD custodian's AML-program obligation.

`query.py` walks those edges in one traversal — the join that plain vector-RAG can't find, because
the cross-sovereign links are edges, not textual similarity.

## Growing it (the intended build order)

1. Add `(title, part)` rows to `ingest.py`'s `MANIFEST` as the obligation surface grows.
2. Ingest the **FINRA Funding Portal Rules** + Regulatory Notices as `tier B` nodes with
   `interprets` edges (never roots), and FINRA AWCs / SEC enforcement as `tier C` nodes with
   `evidenced_by` edges (the post-mortems).
3. Wire the parent project's monitors as `system_controls.check_cmd` (e.g.
   `scripts/fund-custody-check.py`, `finra-portal-check.py`, `badactor-watch.py`).
4. Add a text-retrieval layer (BM25 + local embeddings) over ingested full text; use graph
   expansion (`query.py:expand`) from the retrieval hits.
5. Register every ingestion-schema dependency as a Tier-F `assumptions` row with a live check
   (the parent project's `assumption-check.py` pattern).

## Access

All sources are public, keyless golden sources; SEC hosts require a declared `User-Agent`
(`SEC_CONTACT_EMAIL`). Full method: `docs/edgar-access-guide.md` pattern / `scripts/sec-fetch.sh`
in the parent repo.
