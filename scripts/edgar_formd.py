"""edgar_formd.py - shared Form D access + parse (importable; underscore name on purpose).

Used by screen-offering.py and control-panel.py. Keeps the EDGAR gotchas in ONE place:
  - submissions' primaryDocument for Form D points at the XSLT-rendered HTML
    ("xslFormDX08/primary_doc.xml"); the raw structured XML is the same filename without the
    styling-dir prefix.
  - the AP feed / sec.gov require a compliant User-Agent -> we go through scripts/sec-fetch.sh.
"""
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))


def sec_fetch(url: str) -> str:
    out = subprocess.run(["bash", os.path.join(HERE, "sec-fetch.sh"), url],
                         capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"fetch failed ({out.returncode}) for {url}: {out.stderr.strip()}")
    return out.stdout


def latest_form_d(cik: str):
    """(issuer_name, accession, raw_doc_filename) for the most recent Form D, or exit if none."""
    cik10 = str(int(cik)).zfill(10)
    data = json.loads(sec_fetch(f"https://data.sec.gov/submissions/CIK{cik10}.json"))
    issuer = data.get("name", f"CIK {cik}")
    r = data["filings"]["recent"]
    for form, acc, doc in zip(r["form"], r["accessionNumber"], r["primaryDocument"]):
        if form == "D":
            return issuer, acc, (doc.split("/")[-1] or "primary_doc.xml")
    sys.exit(f"no Form D found for CIK {cik} (issuer: {issuer})")


def fetch_form_d_xml(cik: str, accession: str, raw_doc: str) -> str:
    nodash = accession.replace("-", "")
    return sec_fetch(f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{nodash}/{raw_doc}")


def _ln(tag):
    return tag.split("}")[-1]


def _first_text(root, localname):
    for el in root.iter():
        if _ln(el.tag) == localname and (el.text or "").strip():
            return el.text.strip()
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
    # dateOfFirstSale is either a <value> child or a <yetToOccur> flag
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
    """One call: CIK -> {accession, ...parsed fields}."""
    issuer, accession, raw_doc = latest_form_d(cik)
    data = parse_form_d(fetch_form_d_xml(cik, accession, raw_doc))
    data["accession"] = accession
    data["issuer"] = data.get("issuer") or issuer
    return data
