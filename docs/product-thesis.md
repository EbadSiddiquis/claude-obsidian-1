# Product Thesis (living document)

**One line:** The "counsel-ready, drift-monitored" compliance layer for securities offerings.
Vanta-for-securities-counsel. The product makes an issuer *counsel-ready* and monitors for
*drift*; the lawyer still opines. It assembles and flags. **It never opines.**

> Status: v0.1 (2026-06-29). This is a working thesis captured from conversation, meant to
> be **constantly refined**. Update it whenever the positioning sharpens, and add a line to
> the Revision Log at the bottom. Keep it honest: mark what's conviction vs. open question.

---

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

- ICP: who is the first buyer - the issuer (founder/CFO) or the law firm itself (as a tool
  that makes their associates faster)? Different products.
- Wedge offering type: start with Reg D 506(c) (cleanest, highest volume, verification-heavy)?
- Build vs. partner for accreditation verification.
- How to source/normalize the private evidence (integrations vs. upload).
- What's the minimum defensible "counsel-ready package" a lawyer will actually accept?

## Revision Log

- **v0.1 (2026-06-29):** Initial capture from conversation. Positioning (layer underneath
  authority / Vanta-for-counsel), the never-opine discipline, four loops, moat questions,
  data boundaries. Author: issuer; authority: counsel; us: substrate.
