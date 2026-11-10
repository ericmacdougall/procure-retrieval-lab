"""Deterministic source-identity repair, decided before the sealed evaluation.

Public records can describe the same contract under legal-name/title variants.
Equivalence is intentionally conservative: title, buyer, supplier, value and the
complete contract period must agree after documented punctuation/legal suffix normalization.
"""
import re
from collections import defaultdict
from common import tok

LEGAL={"limited","ltd","plc","llp","inc","incorporated","llc"}


def identity(text):
    words=tok(text)
    while words and words[-1] in LEGAL:
        words.pop()
    return "".join(w[:-3] if w.endswith("ing") and len(w)>7 else w for w in words)


def title_identity(text):
    words=[w for w in tok(text) if w!="and"]
    while words and words[-1] in {"award","notice","subscription","renewal"}:
        words.pop()
    return "".join(words)


def equivalent_groups(docs):
    groups=defaultdict(list)
    for doc in docs:
        # Missing dates cannot establish that two awards are the same event.
        if not doc.get("contract_start") or not doc.get("contract_end"):
            key=(doc["doc_id"],)
        else:
            key=(identity(doc["buyer"]),title_identity(doc["title"]),
                 tuple(sorted(identity(s) for s in doc["suppliers"])),
                 tuple(doc["amounts"]),doc["currency"],doc["contract_start"],doc["contract_end"])
        groups[key].append(doc["doc_id"])
    return {doc_id:sorted(ids) for ids in groups.values() for doc_id in ids}


def repair_questions(questions,docs,withheld):
    by_id={d["doc_id"]:d for d in docs}
    equiv=equivalent_groups(docs)
    supplier_references=defaultdict(list)
    for d in docs:
        if d["doc_id"] not in withheld:
            for supplier in d["suppliers"]:
                supplier_references[(identity(d["buyer"]),title_identity(d["title"]),identity(supplier))].append(d["doc_id"])
    repaired=[]
    changes=[]
    excluded=[]
    for question in questions:
        q=dict(question)
        if not q["gold_doc_ids"]:
            anchor=q["meta"]["withheld_doc"]
            if any(x not in withheld for x in equiv[anchor]):
                excluded.append(dict(id=q["id"],split=q["split"],reason="no_answer_has_available_equivalent_contract_record"))
                continue
            repaired.append(q)
            continue
        q["relevance_groups"]=[]
        for gold in q["gold_doc_ids"]:
            members=[gold]+[x for x in equiv[gold] if x!=gold and x not in withheld]
            q["relevance_groups"].append(members)
        doc=by_id[q["gold_doc_ids"][0]]
        clause=None
        generic=title_identity(doc["title"]) in {"contractnotification","contractawardnotification","contract","notification"}
        alias_collision=False
        if q["slice"]=="adversarial-neardup" and q["meta"].get("disambiguator")=="supplier":
            alias_collision=any(len(supplier_references[(identity(doc["buyer"]),title_identity(doc["title"]),identity(s))])>1 for s in doc["suppliers"])
        if q["slice"]=="paraphrase-heavy":
            clause="The buyer is "+doc["buyer"]+"."
            if doc.get("award_date"):
                clause+=" Use the award dated "+doc["award_date"]+"."
        elif (generic or alias_collision) and doc.get("award_date") and q["meta"].get("field")!="award_date":
            clause="Use the award dated "+doc["award_date"]+"."
        if clause:
            q["text"]=q["text"].rstrip()+" "+clause
            q["identity_clarification"]=clause
        if clause or any(len(g)>1 for g in q["relevance_groups"]):
            changes.append(dict(id=q["id"],split=q["split"],clarified=bool(clause),equivalence_group_sizes=[len(g) for g in q["relevance_groups"]]))
        repaired.append(q)
    return repaired,changes,excluded
