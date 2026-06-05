---
type: meta
title: "Wiki Index"
updated: 2026-04-07
tags:
  - meta
  - index
status: evergreen
related:
  - "[[overview]]"
  - "[[log]]"
  - "[[hot]]"
  - "[[dashboard]]"
  - "[[Wiki Map]]"
  - "[[concepts/_index]]"
  - "[[entities/_index]]"
  - "[[sources/_index]]"
  - "[[LLM Wiki Pattern]]"
  - "[[Hot Cache]]"
  - "[[Compounding Knowledge]]"
  - "[[Andrej Karpathy]]"
---

# Wiki Index

Last updated: 2026-06-05 | Total pages: 52 + 13 (Mode D scaffold) | Sources ingested: 6

Navigation: [[overview]] | [[log]] | [[hot]] | [[dashboard]] | [[Wiki Map]] | [[getting-started]]

---

## Concepts

- [[LLM Wiki Pattern]] — the pattern for building persistent, compounding knowledge bases using LLMs (status: mature)
- [[Hot Cache]] — ~500-word session context file, updated after every ingest and session (status: mature)
- [[Compounding Knowledge]] — why wiki knowledge grows more valuable over time, unlike RAG (status: mature)
- [[Agent Harness Engineering]] — 98.4% infrastructure / 1.6% AI; the harness is the differentiator; 6 production agent design decisions (status: developing)
- [[queryLoop Architecture]] — Claude Code's single AsyncGenerator while-loop; 9-step turn pipeline; 5 stop conditions (status: developing)
- [[5-Layer Compaction]] — graduated context degradation pipeline; Budget Reduction → Snip → Microcompact → Context Collapse → Auto-Compact (status: developing)
- [[Deny-First Permission Model]] — 7 permission modes, 7 safety layers, broad deny always wins, never restore on resume (status: developing)
- [[Claude Code Extensibility]] — 4 mechanisms × 3 injection points; graduated context cost from zero (hooks) to high (MCP) (status: developing)
- [[Subagent Delegation Architecture]] — SkillTool vs AgentTool; 3 isolation modes; sidechain transcripts via flock() (status: developing)
- [[CLAUDE.md Hierarchy]] — 4 levels; user context not system prompt; 9 ordered context sources (status: developing)
- [[Agent Design Space Decisions]] — 6 decisions with alternatives; SWE-bench convergence argument; 3 meta-pattern commitments (status: developing)
- [[Claude Code Ecosystem Reference]] — community repos, blog posts, 8 academic papers; "moat is the harness" independent validation (status: current)
- [[cherry-picks]] — prioritized feature backlog from ecosystem research; 13 features to add to claude-obsidian (status: current)
- [[SVG Diagram Style Guide]] — canonical visual style for all diagrams: Space Grotesk, #0A0A0A dark theme, #E07850 accent, full design tokens (status: evergreen)
- [[Pro Hub Challenge]] — community challenge pattern for building claude-seo/claude-blog extensions; first challenge produced 6 submissions, 5 integrated in v1.9.0 (status: evergreen)
- [[Semantic Topic Clustering]] — SERP-based keyword grouping replacing paid tools; hub-spoke architecture with interactive visualization (status: evergreen)
- [[Search Experience Optimization]] — "read SERPs backwards" methodology for page-type mismatch detection and persona scoring (status: evergreen)
- [[SEO Drift Monitoring]] — "git for SEO" baseline/diff/track with 17 comparison rules and SQLite persistence (status: evergreen)
- [[DragonScale Memory]] — memory-layer spec inspired by the Heighway dragon curve; fold operator, deterministic page addresses, semantic tiling, boundary-first autoresearch (status: shipped v0.4, all four mechanisms opt-in)
- [[Persistent Wiki Artifact]]: durable Markdown page as the LLM's memory object, distinct from ephemeral chat turns (status: developing)
- [[Source-First Synthesis]]: provenance discipline; raw sources stay immutable while the wiki layer is synthesized and cited (status: developing)
- [[Query-Time Retrieval]]: wiki query path synthesizes with citations; complementary to Obsidian's in-vault search (status: developing)

---

## Entities

- [[Andrej Karpathy]] — AI researcher, creator of the LLM Wiki pattern, former Tesla AI director (status: developing)
- [[VILA-Lab]] — research group behind "Dive into Claude Code" (arXiv 2604.14228) (status: developing)
- [[Dive into Claude Code]] — paper; source-level analysis of Claude Code v2.1.88; codifies Agent Harness Engineering as a discipline (status: current)
- [[Ar9av-obsidian-wiki]] — multi-agent compatible LLM Wiki plugin; delta tracking manifest (status: current)
- [[Nexus-claudesidian-mcp]] — native Obsidian plugin + MCP bridge; workspace memory, task management (status: current)
- [[ballred-obsidian-claude-pkm]] — goal cascade PKM; auto-commit hooks, /adopt command (status: current)
- [[rvk7895-llm-knowledge-bases]] — 3-depth query system, Marp slides, parallel deep research (status: current)
- [[kepano-obsidian-skills]] — official skills from Obsidian creator; defuddle, obsidian-bases (status: current)
- [[Claudian-YishenTu]] — native Obsidian plugin embedding Claude Code; plan mode, @mention (status: current)
- [[Claude SEO]] — Tier 4 Claude Code skill for SEO analysis; 23 skills, 17 agents, 30 scripts at v1.9.0 (status: evergreen)

---

## Sources

- [[claude-obsidian-ecosystem-research]] — 2026-04-08 | web research across 16+ repos | 8 wiki pages created
- [[Dive-into-Claude-Code-README]] — 2026-06-05 | VILA-Lab arXiv 2604.14228 | Claude Code v2.1.88 architecture overview
- [[Dive-into-Claude-Code-Architecture]] — 2026-06-05 | VILA-Lab arXiv 2604.14228 | 7-component system, 5-layer subsystems, extensibility, subagents, session persistence
- [[Dive-into-Claude-Code-Build-Agent]] — 2026-06-05 | VILA-Lab arXiv 2604.14228 | 6 design decisions, alternatives, 3 meta-pattern commitments
- [[Dive-into-Claude-Code-Related-Resources]] — 2026-06-05 | VILA-Lab arXiv 2604.14228 | community analysis, reimplementations, blog posts, academic papers

---

## Questions

- [[How does the LLM Wiki pattern work]] — how the pattern works and why it outperforms RAG at human scale (status: developing)

---

## Comparisons

- [[Wiki vs RAG]] — when to use a wiki knowledge base versus RAG; verdict: wiki wins at <1000 pages
- [[claude-obsidian-ecosystem]] — feature matrix of 16+ Claude+Obsidian projects; where claude-obsidian wins and gaps

---

## Decisions

- [[2026-04-14-community-cta-rollout]] - Skool community CTA footer added to 6 skill repos with per-tool frequency rules (status: active)
- [[2026-04-15-slides-and-release-session]] - Claude SEO v1.9.0 slides (15-slide HTML deck) + GitHub release v1.9.0 with PDF asset (status: complete)
- [[2026-04-15-release-report-session]] - Claude SEO v1.9.0 Release Report PDF: dark theme, 13 pages, WeasyPrint layout fixes, Challenge v2 added (status: complete)
- [[2026-04-14-claude-seo-v190-session]] - Claude SEO v1.9.0 Pro Hub Challenge integration: 5 submissions, 4 new skills, 4 review rounds, cybersecurity audit (status: complete)

---

## Domains

<!-- Add domain entries here after scaffold -->

---

## Second Brain (Mode D)

_Added 2026-06-04. Personal life OS layer — goals, learning, people, areas, resources._

### Goals
- [[North Star]] — one-sentence direction; anchor for everything else
- [[Annual Goals]] — 2026 goals table with quarterly focus
- [[Weekly Review Template]] — copy and fill each week

### Areas
- [[areas/_index]] → [[Health]] | [[Career]] | [[Finances]] | [[Creative]]

### Learning
- [[learning/_index]] — concepts being mastered; skills in development

### People
- [[people/_index]] — relationships, shared context, follow-ups

### Resources
- [[resources/_index]] — books, courses, tools, articles worth keeping
