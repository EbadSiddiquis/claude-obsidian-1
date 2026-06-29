---
type: concept
title: "EDGAR Data Access"
complexity: advanced
domain: securities-regulation
aliases:
  - "CIK"
  - "Central Index Key"
  - "Accession Number"
  - "EDGAR Identifiers"
created: 2026-06-29
updated: 2026-06-29
tags:
  - concept
  - securities
  - sec
  - edgar
  - data
status: developing
related:
  - "[[EDGAR]]"
  - "[[EDGAR APIs]]"
  - "[[EDGAR Bulk Data]]"
  - "[[XBRL]]"
  - "[[concepts/_index]]"
  - "[[index]]"
sources:
  - "[[SEC.gov - Accessing EDGAR Data]]"
  - "[[SEC.gov - New Rate Control Limits]]"
---

# EDGAR Data Access

The practical identifiers and rules for retrieving filings from [[EDGAR]] programmatically. (Source: [[SEC.gov - Accessing EDGAR Data]])

---

## CIK (Central Index Key)

- A unique **10-digit** number the SEC assigns to each registrant/filer.
- **Never changes** even if the company renames or changes ticker - the most reliable long-term identifier. (Source: [[SEC.gov - Accessing EDGAR Data]])
- Find a CIK by searching EDGAR by company name or ticker (e.g., IBM -> CIK `0000051143`). Leading zeros are often dropped in some access paths.
- In `data.sec.gov` API paths, CIK is **zero-padded to 10 digits**.

## Accession number

The unique ID of an accepted submission, format `XXXXXXXXXX-YY-NNNNNN`: (Source: [[SEC.gov - Accessing EDGAR Data]])

- First block = the **CIK of the submitter** (company or filer agent).
- `YY` = the **year**.
- `NNNNNN` = a **sequential count** of that filer's submissions, reset each calendar year.
- Example: IBM's Oct 2013 10-Q = `0000051143-13-000007`.

## Fair-access rules (important)

- **10 requests/second** hard cap **per user/IP**, regardless of machine count. (Source: [[SEC.gov - New Rate Control Limits]])
- A descriptive **User-Agent header** (organization name + contact email) is **required**; requests without it are blocked.
- Exceeding the limit returns **HTTP 403** and blocks the IP for ~**10 minutes**.

> [!note] This rate-control + User-Agent rule is the same mechanism that returned 403 to this vault's automated WebFetch attempts against sec.gov. It resolves the earlier open question on [[EDGAR APIs]].

## Confidence

**high** - CIK/accession format and the 10 req/s + User-Agent rule are documented by the SEC and corroborated across multiple developer sources.
