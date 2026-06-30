"""edgar_formd.py - shared EDGAR offering-form access + parse (importable; underscore name on purpose).

Used by screen-offering.py and control-panel.py. Keeps the EDGAR gotchas in ONE place:
  - submissions' primaryDocument points at the XSLT-rendered HTML (Form D: "xslFormDX08/primary_doc.xml";
    Form C: "xslC_X01/primary_doc.xml"); the raw structured XML is the same filename without the
    styling-dir prefix (split off via doc.split("/")[-1]).
  - sec.gov / data.sec.gov require a compliant User-Agent -> we go through scripts/sec-fetch.sh.

Despite the file name, this module now drives BOTH Form D (Reg D 506(b)/(c)) and Form C (Reg CF /
Section 4(a)(6) funding-portal raises). load_form_d / load_form_c return the same envelope shape
(issuer, accession, related_persons, all_filings, filing_date) so a single control panel can
dispatch on a framework's `driver` field without special-casing the consumer.
"""
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))

# EDGAR form types that represent a securities OFFERING (used for the integration window check).
OFFERING_FORMS = {"D", "D/A", "1-A", "1-A/A", "1-A POS", "S-1", "S-1/A", "C", "C/A", "C-U",
                  "253G1", "253G2", "253G3", "S-3", "S-3/A"}


def sec_fetch(url: str) -> str:
    out = subprocess.run(["bash", os.path.join(HERE, "sec-fetch.sh"), url],
                         capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"fetch failed ({out.returncode}) for {url}: {out.stderr.strip()}")
    return out.stdout


def fetch_submissions(cik: str) -> dict:
    cik10 = str(int(cik)).zfill(10)
    return json.loads(sec_fetch(f"https://data.sec.gov/submissions/CIK{cik10}.json"))


def list_filings(subs: dict) -> list:
    """[{form, date, accession, primary_document}] for the issuer's recent filings. primary_document
    is the submissions' primaryDocument (the XSLT-styled path); strip its dir prefix for raw XML."""
    r = subs["filings"]["recent"]
    return [{"form": f, "date": d, "accession": a, "primary_document": pd}
            for f, d, a, pd in zip(r["form"], r["filingDate"], r["accessionNumber"], r["primaryDocument"])]


def _pick_form_d(subs: dict):
    r = subs["filings"]["recent"]
    for form, acc, doc in zip(r["form"], r["accessionNumber"], r["primaryDocument"]):
        if form == "D":
            return acc, (doc.split("/")[-1] or "primary_doc.xml")
    return None


def fetch_archive_doc(cik: str, accession: str, raw_doc: str) -> str:
    """Fetch a document from an EDGAR filing's archive directory (form-agnostic)."""
    nodash = accession.replace("-", "")
    return sec_fetch(f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{nodash}/{raw_doc}")


# Back-compat alias: the fetch is just an archive GET, not Form-D-specific.
fetch_form_d_xml = fetch_archive_doc


def _ln(tag):
    return tag.split("}")[-1]


def _first_text(root, localname):
    for el in root.iter():
        if _ln(el.tag) == localname and (el.text or "").strip():
            return el.text.strip()
    return None


def _find(root, localname):
    """First element (in document order) whose localname matches; None if absent."""
    for el in root.iter():
        if _ln(el.tag) == localname:
            return el
    return None


def parse_form_d(xml: str) -> dict:
    """Structured extract of the fields the control panel needs (namespace-agnostic)."""
    root = ET.fromstring(xml.encode("utf-8"))

    people = []
    for node in root.iter():
        if _ln(node.tag) != "relatedPersonInfo":
            continue
        first = last = ""
        rels = []
        for el in node.iter():
            ln, txt = _ln(el.tag), (el.text or "").strip()
            if ln == "firstName":
                first = txt
            elif ln == "lastName":
                last = txt
            elif ln == "relationship" and txt:
                rels.append(txt)
        name = " ".join(p for p in (first, last) if p).strip()
        if name:
            people.append({"name": name, "relationships": rels})

    exemptions = [el.text.strip() for el in root.iter()
                  if _ln(el.tag) == "item" and (el.text or "").strip()]

    has_na = _first_text(root, "hasNonAccreditedInvestors")
    first_sale = None
    for node in root.iter():
        if _ln(node.tag) == "dateOfFirstSale":
            first_sale = _first_text(node, "value") or ("yet-to-occur" if _first_text(node, "yetToOccur") else None)
            break

    return {
        "issuer": _first_text(root, "entityName"),
        "related_persons": people,
        "exemptions": exemptions,
        "total_offering_amount": _first_text(root, "totalOfferingAmount"),
        "total_sold": _first_text(root, "totalAmountSold"),
        "total_remaining": _first_text(root, "totalRemaining"),
        "has_non_accredited": (None if has_na is None else has_na.lower() == "true"),
        "num_already_invested": _first_text(root, "totalNumberAlreadyInvested"),
        "date_of_first_sale": first_sale,
    }


def load_form_d(cik: str) -> dict:
    """One call: CIK -> {issuer, accession, parsed fields, all_filings, filing_date}."""
    subs = fetch_submissions(cik)
    issuer = subs.get("name", f"CIK {cik}")
    picked = _pick_form_d(subs)
    if not picked:
        sys.exit(f"no Form D found for CIK {cik} (issuer: {issuer})")
    accession, raw_doc = picked
    data = parse_form_d(fetch_archive_doc(cik, accession, raw_doc))
    data["accession"] = accession
    data["form_type"] = "D"
    data["issuer"] = data.get("issuer") or issuer
    data["all_filings"] = list_filings(subs)
    data["filing_date"] = next((f["date"] for f in data["all_filings"] if f["accession"] == accession), None)
    return data


# ---------------------------------------------------------------------------
# Form C (Regulation Crowdfunding / Section 4(a)(6)) - funding-portal raises.
# Form C carries the issuer, the SINGLE intermediary (funding portal / BD) by CIK + CRD +
# funding-portal file number (the "007-" prefix), target/maximum offering amounts, the deadline,
# and the state-jurisdiction list. Note what it does NOT carry: Form D's exemption codes and
# accreditation fields are absent (Reg CF has no accreditation gate), so the CF evaluators key off
# offering amounts + the intermediary block + signature persons, not exemption codes.
# ---------------------------------------------------------------------------

def _pick_form_c(subs: dict):
    # The offering's Form C is "C" (initial) or "C/A" (amendment). Intentionally NOT C-U
    # (progress update) or C-AR / C-AR/A (annual report) / C-TR (termination) - those are
    # follow-on filings with a different schema, not the offering document this panel drives.
    r = subs["filings"]["recent"]
    for form, acc, doc in zip(r["form"], r["accessionNumber"], r["primaryDocument"]):
        if form in ("C", "C/A"):
            return acc, (doc.split("/")[-1] or "primary_doc.xml"), form
    return None


def parse_form_c(xml: str) -> dict:
    """Structured extract of the Form C fields the funding-portal panel needs (namespace-agnostic)."""
    root = ET.fromstring(xml.encode("utf-8"))

    # signaturePersons -> covered persons for the Reg CF 227.503 bad-actor screen.
    people = []
    for node in root.iter():
        if _ln(node.tag) != "signaturePerson":
            continue
        name = title = ""
        for el in node.iter():
            ln, txt = _ln(el.tag), (el.text or "").strip()
            if ln == "personSignature":
                name = txt
            elif ln == "personTitle":
                title = txt
        if name:
            people.append({"name": name, "relationships": [title] if title else []})

    states = [el.text.strip() for el in root.iter()
              if _ln(el.tag) == "issueJurisdictionSecuritiesOffering" and (el.text or "").strip()]

    # The intermediary block (companyName / commissionCik / commissionFileNumber / crdNumber)
    # lives directly under issuerInformation as siblings of issuerInfo; scope the lookup there so
    # a generic localname like companyName can't be captured from some other block by a whole-tree
    # first-match. issuerInfo (the issuer's own subtree) carries nameOfIssuer, not companyName, so
    # this scope stays unambiguous. Fall back to the whole tree if the block is absent.
    iinfo = _find(root, "issuerInformation") or root

    return {
        "issuer": _first_text(root, "nameOfIssuer"),
        "related_persons": people,
        "intermediary_name": _first_text(iinfo, "companyName"),
        "intermediary_cik": _first_text(iinfo, "commissionCik"),
        "intermediary_file_number": _first_text(iinfo, "commissionFileNumber"),
        "intermediary_crd": _first_text(iinfo, "crdNumber"),
        "offering_amount": _first_text(root, "offeringAmount"),
        "maximum_offering_amount": _first_text(root, "maximumOfferingAmount"),
        "security_type": _first_text(root, "securityOfferedType"),
        "price": _first_text(root, "price"),
        "num_securities": _first_text(root, "noOfSecurityOffered"),
        "over_subscription_accepted": _first_text(root, "overSubscriptionAccepted"),
        "deadline_date": _first_text(root, "deadlineDate"),
        "state_jurisdictions": states,
    }


def list_form_c_intermediaries(cik: str, all_filings: list, cap: int = 10):
    """For each of the issuer's Form C / C-A filings, fetch + parse its primary_doc.xml and pull the
    named intermediary - so the single-intermediary control (227.300(b)) can cross-check whether the
    issuer's public Form C record names one intermediary or several. Returns (rows, truncated).

    Capped at `cap` fetches (newest-first) to bound cost; `truncated` flags when more existed (the
    no-silent-caps principle - the caller surfaces it)."""
    # Up to `cap` sequential sec-fetch.sh subprocess calls; the SEC 10-req/s ceiling is the cost floor.
    cfs = [f for f in all_filings if f.get("form", "").upper() in ("C", "C/A")]
    truncated = len(cfs) > cap
    rows = []
    for f in cfs[:cap]:
        raw_doc = (f.get("primary_document") or "").split("/")[-1] or "primary_doc.xml"
        try:
            fc = parse_form_c(fetch_archive_doc(cik, f["accession"], raw_doc))
        except (Exception, SystemExit):
            # A single unparseable filing OR a failed fetch (sec_fetch sys.exits on non-zero rc) must
            # not sink the cross-check; it is dropped here and surfaces as a parse-gap to the caller,
            # which refuses a clean single-intermediary clearance when rows < the C/C-A filings present.
            continue
        rows.append({**f,
                     "intermediary_cik": fc.get("intermediary_cik"),
                     "intermediary_name": fc.get("intermediary_name"),
                     "intermediary_file_number": fc.get("intermediary_file_number"),
                     "deadline_date": fc.get("deadline_date")})
    return rows, truncated


def load_form_c(cik: str) -> dict:
    """One call: CIK -> {issuer, accession, parsed Form C fields, all_filings, filing_date}.

    Same envelope shape as load_form_d so the control panel can dispatch on `driver` uniformly.
    """
    subs = fetch_submissions(cik)
    issuer = subs.get("name", f"CIK {cik}")
    picked = _pick_form_c(subs)
    if not picked:
        sys.exit(f"no Form C found for CIK {cik} (issuer: {issuer})")
    accession, raw_doc, form = picked
    data = parse_form_c(fetch_archive_doc(cik, accession, raw_doc))
    data["accession"] = accession
    data["form_type"] = form
    data["issuer"] = data.get("issuer") or issuer
    data["all_filings"] = list_filings(subs)
    data["filing_date"] = next((f["date"] for f in data["all_filings"] if f["accession"] == accession), None)
    return data
