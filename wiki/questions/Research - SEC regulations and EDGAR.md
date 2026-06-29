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

## Reg CF / Crowdfunding Funding Portals (Pass 2)

- **[[Regulation Crowdfunding]]** (Title III of the JOBS Act, effective 2016) lets private companies raise up to **$5M/12 months** from the public, including non-accredited investors. (Source: [[SEC.gov - Regulation Crowdfunding]])
- Every Reg CF raise must run through a registered **[[Funding Portal]]** or broker-dealer. A funding portal is a FINRA-member intermediary that **cannot** give advice, solicit, hold investor funds, or take transaction-based pay - a lighter-weight model than a broker-dealer. (Source: [[Funding Portal]])
- Portals register on **Form Funding Portal via [[EDGAR]]** and join **[[Financial Industry Regulatory Authority|FINRA]]**; FINRA runs the Funding Portal Registration Depository and the Funding Portal Rules. **83 portals** were registered as of end-2024. (Source: [[FINRA - Funding Portals]])
- Issuers file **[[Form C]]** before the raise and **Form C-AR** annually (within 120 days of FY-end) on EDGAR. (Source: [[Form C]])
- Market is concentrated: 2025 Reg CF dollars led by **[[Wefunder]]** (~$109M, ~33%), **[[StartEngine]]** (~$89M, ~24%), DealMaker (~$66M), **[[Republic (crowdfunding)|Republic]]** (~$20M). (Source: [[Angel Investors Network - Reg CF Platform Comparison]])

## XBRL & Structured Data (Pass 3)

- **[[XBRL]]** (eXtensible Business Reporting Language) is the structured-data standard for financial info in EDGAR filings: each figure is tagged against the FASB **US GAAP taxonomy** (~17,000 tags) so filings are machine-readable. (Source: [[XBRL]])
- **Inline XBRL (iXBRL)** embeds tags directly in the HTML filing (one human- + machine-readable document). Adopted June 28, 2018; phased in by filer size FY-ends June 2019 -> June 2021. Required for cover page + financials in 10-K/10-Q and parts of 8-K/proxy. (Source: [[XBRL]])
- XBRL history: mandate began **2009** (large accelerated filers), all filers by **2012**; this XBRL data powers the [[EDGAR APIs]]. (Source: [[XBRL]])
- The **[[Financial Data Transparency Act]]** (FDTA, Dec 2022) extends machine-readable standards across **nine federal agencies** (incl. SEC, Treasury, Fed, FDIC, CFTC...). Adopts a common **LEI (ISO 17442)**; standardizes format without requiring new data collection. Proposed Aug 2024; final joint rule in 2026. (Source: [[Financial Data Transparency Act]])

## Recent Rulemaking 2023-2026 (Pass 4)

The era's rules split by type ([[Recent SEC Rulemaking and Litigation 2023-2026]]):

- **In effect:** [[SEC Cybersecurity Disclosure Rules]] (Jul 2023) - 8-K **Item 1.05** material-incident disclosure within **4 business days** + annual Reg S-K **Item 106** governance; and [[T+1 Settlement Cycle]] (Rule 15c6-1, effective **May 28, 2024**).
- **Vacated:** the share-repurchase ("buyback") disclosure rule (May 2023) was struck down by the **Fifth Circuit on Dec 19, 2023** as arbitrary and capricious under the APA. (Source: [[Orrick - Fifth Circuit Vacates Share Repurchase Rules]])
- **Stayed -> rescission proposed:** the [[SEC Climate Disclosure Rule]] (Mar 2024) was stayed Apr 2024, the SEC dropped its defense Mar 2025, and a **2026 rescission** is now proposed. (Source: [[SEC Climate Disclosure Rule]])
- Pattern: disclosure-expansion mandates drew successful APA / major-questions challenges; operational rules (T+1, cyber-incident) stuck.

## Private-Offering Exemptions (Pass 5)

The Securities Act requires registration unless an exemption applies ([[Exempt Offerings]]):

- **[[Regulation D]]** is the private workhorse. **Rule 506(b)**: no general solicitation, unlimited accredited + up to 35 sophisticated, self-verification. **Rule 506(c)**: general solicitation allowed but accredited-only with "reasonable steps to verify." Both file a **Form D** within 15 days of first sale. (Source: [[Regulation D]])
- **[[Regulation A]]** ("mini-IPO") is public-facing: **Tier 1 up to $20M**, **Tier 2 up to $75M** per 12 months, via **Form 1-A** qualified by the SEC; Tier 2 preempts state review. (Source: [[Regulation A]])
- **[[Accredited Investor]]**: income > $200k ($300k joint) or net worth > $1M (ex-residence); since Dec 2020, **Series 7/65/82** holders also qualify. (Source: [[Accredited Investor]])
- **[[Rule 144]]** is the resale exit: 6-month (reporting) / 1-year (non-reporting) holding period; affiliates also face a 1%-or-weekly-volume cap, manner-of-sale rules, and Form 144. (Source: [[Rule 144]])

## Key Entities

- [[U.S. Securities and Exchange Commission]]: the federal regulator that administers securities law and operates EDGAR.
- [[Financial Industry Regulatory Authority]]: SRO overseeing broker-dealers and funding portals under SEC supervision.
- [[Wefunder]], [[StartEngine]], [[Republic (crowdfunding)]]: the leading Reg CF funding portals.

## Key Concepts

- [[EDGAR]]: the SEC's electronic filing and dissemination system.
- [[EDGAR Next]]: 2024–2025 modernization of filer access (Login.gov, MFA, role-based admin).
- [[Federal Securities Laws]]: the statutes the SEC enforces (1933 Act through JOBS Act 2012).
- [[SEC Filing Types]]: the standardized forms (10-K, 10-Q, 8-K, S-1, 13D/G, Forms 3/4/5, etc.).
- [[EDGAR APIs]]: the public `data.sec.gov` JSON endpoints and full-text search.
- [[Regulation Crowdfunding]]: the Reg CF exemption (Title III JOBS Act); $5M public raises via registered intermediaries.
- [[Funding Portal]]: FINRA-member Reg CF intermediary; lighter-weight than a broker-dealer.
- [[Form C]]: the Reg CF offering statement (plus C-AR annual report) filed on EDGAR.
- [[XBRL]]: structured-data tagging standard (inline XBRL) for EDGAR financial filings.
- [[Financial Data Transparency Act]]: 2022 law mandating uniform machine-readable data across nine financial regulators.
- [[SEC Cybersecurity Disclosure Rules]]: 8-K Item 1.05 + Reg S-K Item 106 (in effect, 2023).
- [[SEC Climate Disclosure Rule]]: adopted 2024, stayed, rescission proposed 2026.
- [[T+1 Settlement Cycle]]: one-day settlement, effective May 2024.
- [[Recent SEC Rulemaking and Litigation 2023-2026]]: roundup of the era's rules and their fates.
- [[Exempt Offerings]]: the menu of registration exemptions (Reg D / Reg A / Reg CF / 4(a)(2)).
- [[Regulation D]], [[Regulation A]], [[Accredited Investor]], [[Rule 144]]: the private-capital and resale exemptions.

## Contradictions

- Headline scale figures differ across sources: Wikipedia cites "17M filings (May 2025)" while older SEC material cites "36M documents." These measure different units (submissions vs. constituent documents) rather than truly conflicting. (Source: [[EDGAR]])
- December 2025 EDGAR Next sub-deadlines vary by a few days between law-firm summaries (Dec 19 vs Dec 22). The SEC final rule is authoritative. (Source: [[EDGAR Next]])

## Open Questions

- **EDGAR API rate limits:** the exact current fair-access limit (commonly cited as 10 req/s) was not re-verified - SEC.gov blocked automated fetch (HTTP 403). Confirm from the official Developer Resources page.
- **EDGAR Next machine-to-machine filing:** how API tokens / technical-administrator roles work for automated filing under the new model needs a dedicated pass.
- **XBRL & structured-data mandate:** covered in Pass 3 (XBRL/iXBRL + FDTA). Remaining: exact FDTA 2026 final-rule effective date; per-agency SEC implementing rules.
- **Recent rulemaking (2023-2026):** covered in Pass 4 (cyber, climate, buybacks, T+1). Remaining: precise 2026 climate-rescission final text; any new 2026 disclosure proposals.
- **Regulation S-K / S-X:** the detailed disclosure-content and financial-statement rules behind the forms were not yet covered.
- **Exemptions:** covered in Pass 5 (Reg D, Reg A, Rule 144, accredited investor) and Pass 2 (Reg CF). Remaining: Section 4(a)(2) case law; intrastate (Rule 147/147A); pending accredited-investor expansion legislation.
- **SEC enforcement & structure:** divisions, the Wells process, whistleblower program, administrative vs federal-court proceedings still open.
- **Reg CF financial-statement tiers:** exact dollar thresholds for self-certified vs reviewed vs audited financials (Rule 201(t)) still need verification.

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
- **Pass 2 (2026-06-29):** Reg CF crowdfunding funding portals - Regulation Crowdfunding, Funding Portal, Form C, FINRA, and the three leading portals (Wefunder/StartEngine/Republic). 14 pages filed.
- **Pass 3 (2026-06-29):** XBRL & structured data - XBRL/inline XBRL, Financial Data Transparency Act, FASB. 8 pages filed.
- **Pass 4 (2026-06-29):** Recent rulemaking 2023-2026 - cybersecurity (8-K Item 1.05), climate disclosure, buyback vacatur, T+1, plus a litigation roundup. 9 pages filed. Wiki-lint run (full vault): 0 orphans, fixed 3 self-introduced dead links, flagged pre-existing ones for human review.
- **Pass 5 (2026-06-29):** Private-offering exemptions - Exempt Offerings umbrella, Regulation D (506b/506c), Regulation A (Tier 1/2), Accredited Investor, Rule 144. 11 pages filed.
