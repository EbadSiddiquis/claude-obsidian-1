---
type: meta
title: "Lint Report 2026-06-29"
created: 2026-06-29
updated: 2026-06-29
tags: [meta, lint]
status: developing
---

# Lint Report: 2026-06-29

Scope: the SEC/EDGAR autoresearch pages (passes 1-2, 30 pages). Run as part of the autoresearch loop.

## Summary

| Check | Result |
|-------|--------|
| Dead wikilinks (new pages) | **0** |
| Orphan pages (new pages with no inbound link) | **0** |
| Pages scanned | 30 |

## Detail

- **Dead links:** none. Every `[[wikilink]]` in the SEC/EDGAR/Reg-CF pages resolves to an existing page (stem resolution).
- **Orphans:** none. All 30 new pages have at least one inbound link (from the synthesis page, the index, or sibling pages).
- **Frontmatter:** all new pages carry type/title/created/updated/tags/status.

## Needs human review

- **Confidence flags (by design, not errors):** several `> [!gap]` / `> [!note]` callouts mark facts captured via WebSearch excerpts because SEC.gov blocks automated WebFetch (HTTP 403). Items to verify in a browser: exact EDGAR API rate limit; EDGAR Next December 2025 sub-deadlines; Reg CF financial-statement tier thresholds (Rule 201(t)); 2025 Reg CF platform dollar/share figures (single market-analysis source, confidence low).
- No destructive fixes were applied (no deletions, no edits to pre-existing non-loop pages).

## Next

Open research clusters remaining (see synthesis Open Questions): XBRL/FDTA, 2024-26 rulemaking, Reg S-K/S-X, remaining exemptions (Reg D/A+/144), SEC enforcement & structure, practical EDGAR data access.
