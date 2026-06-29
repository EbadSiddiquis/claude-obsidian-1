---
type: synthesis
title: "Research: SEC regulations and EDGAR"
created: 2026-06-29
updated: 2026-06-29
tags:
  - research
  - securities
  - sec
  - edgar
  - regulation
status: developing
related:
  - "[[U.S. Securities and Exchange Commission]]"
  - "[[EDGAR]]"
  - "[[EDGAR Next]]"
  - "[[SEC Filing Types]]"
  - "[[EDGAR APIs]]"
  - "[[Federal Securities Laws]]"
  - "[[index]]"
sources:
  - "[[SEC.gov - About EDGAR]]"
  - "[[SEC.gov - Transition to EDGAR Next]]"
  - "[[SEC.gov - EDGAR APIs]]"
  - "[[investor.gov - Laws That Govern the Securities Industry]]"
  - "[[Wikipedia - EDGAR]]"
  - "[[Wikipedia - Securities Exchange Act of 1934]]"
  - "[[sec-api.io - Full-Text Search API Docs]]"
  - "[[edgar.tools - SEC Filing Types Explained]]"
  - "[[Nuvo Group - EDGAR Next Transition]]"
---

# Research: SEC regulations and EDGAR

## Overview

U.S. securities regulation rests on a **mandatory-disclosure** model: the [[U.S. Securities and Exchange Commission|SEC]] requires public companies to file standardized information, and [[EDGAR]] is the electronic pipe through which those filings are submitted and published. The legal obligations come from the [[Federal Securities Laws]] (1933 Act onward); [[SEC Filing Types]] are the instruments; [[EDGAR APIs]] expose the data; and [[EDGAR Next]] is the 2025 modernization of how filers authenticate.

## Key Findings

- The system splits cleanly by market stage: the **Securities Act of 1933** governs primary-market offerings (register before you sell), while the **Securities Exchange Act of 1934** created the SEC and governs ongoing secondary-market reporting. (Source: [[Federal Securities Laws]])
- **EDGAR** automates collection, validation, indexing, and public dissemination of filings; it accepts HTML, ASCII, XML, and XBRL, runs 6am–10pm ET on weekdays, and is free to the public. It holds 17M+ filings and processes thousands per day. (Source: [[EDGAR]])
- The principal periodic forms are the **10-K** (audited annual), **10-Q** (unaudited quarterly), and **8-K** (material events within 4 business days); **S-1** registers a public offering. (Source: [[SEC Filing Types]])
- **EDGAR Next** (final rule Dec 27, 2024) is the biggest filer-access overhaul in 20+ years: Login.gov + multi-factor authentication, no shared credentials, and at least two account administrators per filer. Compliance was required by **Sept 15, 2025**. (Source: [[EDGAR Next]])
- EDGAR data is programmatically accessible via `data.sec.gov` JSON APIs (submissions, company facts/concept/frames) and a full-text search covering filings since 2001, indexed in under 60 seconds - **no API key required**, but a declared User-Agent and rate limits apply. (Source: [[EDGAR APIs]])

## Key Entities

- [[U.S. Securities and Exchange Commission]]: the federal regulator that administers securities law and operates EDGAR.

## Key Concepts

- [[EDGAR]]: the SEC's electronic filing and dissemination system.
- [[EDGAR Next]]: 2024–2025 modernization of filer access (Login.gov, MFA, role-based admin).
- [[Federal Securities Laws]]: the statutes the SEC enforces (1933 Act through JOBS Act 2012).
- [[SEC Filing Types]]: the standardized forms (10-K, 10-Q, 8-K, S-1, 13D/G, Forms 3/4/5, etc.).
- [[EDGAR APIs]]: the public `data.sec.gov` JSON endpoints and full-text search.

## Contradictions

- Headline scale figures differ across sources: Wikipedia cites "17M filings (May 2025)" while older SEC material cites "36M documents." These measure different units (submissions vs. constituent documents) rather than truly conflicting. (Source: [[EDGAR]])
- December 2025 EDGAR Next sub-deadlines vary by a few days between law-firm summaries (Dec 19 vs Dec 22). The SEC final rule is authoritative. (Source: [[EDGAR Next]])

## Open Questions

- **EDGAR API rate limits:** the exact current fair-access limit (commonly cited as 10 req/s) was not re-verified - SEC.gov blocked automated fetch (HTTP 403). Confirm from the official Developer Resources page.
- **EDGAR Next machine-to-machine filing:** how API tokens / technical-administrator roles work for automated filing under the new model needs a dedicated pass.
- **XBRL & structured-data mandate:** the Financial Data Transparency Act (FDTA) and inline XBRL requirements were not yet researched.
- **Recent rulemaking (2024–2026):** climate disclosure, cybersecurity incident disclosure (8-K Item 1.05), and share-repurchase rules are not yet covered.
- **Regulation S-K / S-X:** the detailed disclosure-content and financial-statement rules behind the forms were not yet covered.
- **Enforcement & exemptions:** Reg D, Reg A+, Reg CF (crowdfunding) and the SEC enforcement process remain open.

## Sources

- [[SEC.gov - About EDGAR]]: SEC, official
- [[SEC.gov - Transition to EDGAR Next]]: SEC, 2025-03-24
- [[SEC.gov - EDGAR APIs]]: SEC, official
- [[investor.gov - Laws That Govern the Securities Industry]]: SEC, official
- [[Wikipedia - EDGAR]]: Wikipedia, 2026
- [[Wikipedia - Securities Exchange Act of 1934]]: Wikipedia, 2026
- [[sec-api.io - Full-Text Search API Docs]]: sec-api.io
- [[edgar.tools - SEC Filing Types Explained]]: edgar.tools
- [[Nuvo Group - EDGAR Next Transition]]: The Nuvo Group, 2025

---

## Research Log

- **Pass 1 (2026-06-29):** Broad sweep - laws, EDGAR system, filing types, EDGAR Next, APIs. 16 pages filed.
