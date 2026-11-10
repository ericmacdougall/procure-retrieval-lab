"""Stage normalise: raw OCDS release packages -> data/docs/documents.jsonl + data/manifest.jsonl.

One document per OCDS process (ocid): the latest award-stage release.  Contact points are never copied.
E-mail addresses and phone numbers inside free text are scrubbed.
"""
import glob
import gzip
import json
import os
import re
import sys
import datetime as dt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import RAW, DOCS, ROOT, sha256_file, sha256_text, write_jsonl

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"(?<!\d)(?:\+?44|0)[\d ()-]{8,14}\d")
WS = re.compile(r"\s+")


def g(d, *path, default=None):
    for p in path:
        if isinstance(d, dict):
            d = d.get(p)
        elif isinstance(d, list) and isinstance(p, int) and p < len(d):
            d = d[p]
        else:
            return default
        if d is None:
            return default
    return d


def clean(s):
    s = EMAIL.sub("[email]", s or "")
    s = PHONE.sub("[phone]", s)
    return WS.sub(" ", s).strip()


def day(s):
    return s[:10] if isinstance(s, str) and len(s) >= 10 else None


def to_doc(r):
    awards = r.get("awards") or []
    good = [a for a in awards if g(a, "value", "amount") and (a.get("suppliers") or [])]
    if not good:
        return None
    title = clean(g(r, "tender", "title", default=""))
    buyer = clean(g(r, "buyer", "name", default=""))
    if len(title) < 5 or not buyer:
        return None
    sup = []
    for a in good:
        for s in a["suppliers"]:
            nm = clean(s.get("name", ""))
            if nm and nm not in sup:
                sup.append(nm)
    if not sup:
        return None
    amounts = [float(a["value"]["amount"]) for a in good]
    notice_url = g(good[0], "documents", 0, "url", default="")
    ocid = r["ocid"]
    doc = dict(
        doc_id="N" + sha256_text(ocid)[:12],
        ocid=ocid,
        release_id=r.get("id"),
        notice_url=notice_url,
        title=title,
        description=clean(g(r, "tender", "description", default=""))[:3000],
        buyer=buyer,
        suppliers=sup,
        n_awards=len(good),
        amounts=amounts,
        total_value=sum(amounts),
        currency=g(good[0], "value", "currency", default="GBP"),
        award_date=day(g(good[0], "date")),
        published=day(g(good[0], "datePublished")) or day(r.get("date")),
        contract_start=day(g(good[0], "contractPeriod", "startDate")) or day(g(r, "tender", "contractPeriod", "startDate")),
        contract_end=day(g(good[0], "contractPeriod", "endDate")) or day(g(r, "tender", "contractPeriod", "endDate")),
        cpv=g(r, "tender", "classification", "id"),
        cpv_text=clean(g(r, "tender", "classification", "description", default="")),
        method=clean(g(r, "tender", "procurementMethodDetails", default="")),
        category=g(r, "tender", "mainProcurementCategory"),
        sme=g(r, "tender", "suitability", "sme"),
        release_date=r.get("date"),
    )
    return doc


def main():
    files = sorted(glob.glob(os.path.join(RAW, "*.json.gz")))
    last = os.environ.get("AX11_LAST_WINDOW")
    if last:
        files = [f for f in files if os.path.basename(f)[:11] <= last]
    best = dict()
    n_rel = 0
    man = []
    for fn in files:
        man.append(dict(file=os.path.basename(fn), bytes=os.path.getsize(fn), sha256=sha256_file(fn)))
        pk = json.loads(gzip.open(fn).read())
        lic = pk.get("license")
        for r in pk.get("releases", []):
            n_rel += 1
            d = to_doc(r)
            if d is None:
                continue
            old = best.get(d["ocid"])
            if old is None or (d["release_date"] or "") > (old["release_date"] or ""):
                best[d["ocid"]] = d
    docs = sorted(best.values(), key=lambda d: d["doc_id"])
    # exact content duplicates (different ocid, same everything that matters): keep one
    seen = set()
    out = []
    ndup = 0
    for d in docs:
        key = sha256_text(json.dumps([d["title"], d["description"], d["buyer"], d["suppliers"], d["amounts"], d["award_date"]]))
        if key in seen:
            ndup += 1
            continue
        seen.add(key)
        out.append(d)
    write_jsonl(DOCS, out)
    snap = dt.date.today().isoformat()
    write_jsonl(os.path.join(ROOT, "data", "ocds", "manifest.jsonl"), man)
    summary = dict(
        source="UK Contracts Finder OCDS API (https://www.contractsfinder.service.gov.uk/Published/Notices/OCDS/Search, stages=award)",
        licence="Open Government Licence v3.0 (http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/)",
        snapshot_date=snap,
        raw_files=len(files),
        releases_read=n_rel,
        documents=len(out),
        dropped_exact_duplicates=ndup,
        documents_sha256=sha256_file(DOCS),
        raw_manifest_sha256=sha256_file(os.path.join(ROOT, "data", "ocds", "manifest.jsonl")),
    )
    with open(os.path.join(ROOT, "data", "ocds", "SNAPSHOT.json"), "w") as f:
        json.dump(summary, f, indent=1, sort_keys=True)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
