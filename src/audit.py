"""Label-noise audit.  (1) deterministic checks over every question, (2) LLM judge packets for a stratified sample.

Usage: python src/audit.py det            # deterministic check on train/dev/testlock (held-out is checked at merge time)
       python src/audit.py packets        # writes llm-io/audit-in-NNN.jsonl (>= 154 questions, 22 per slice)
       python src/audit.py score          # reads llm-io/audit-out-NNN.jsonl and writes results/audit.json
"""
import json
import os
import random
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import QDIR, ROOT, SEED, read_jsonl, write_jsonl, tok
from render import doc_text, fields, money
import metrics as M

LLMIO = os.path.join(ROOT, "llm-io")
PER_SLICE = 22


def norm(s):
    return " ".join(tok(s))


def det_check(qs, docs_all, withheld):
    """Return dict qid -> list of failure codes (empty list = clean)."""
    by_id = dict((d["doc_id"], d) for d in docs_all)
    corpus = [d for d in docs_all if d["doc_id"] not in withheld]
    tb = defaultdict(list)
    desc = defaultdict(list)
    for d in corpus:
        tb[(norm(d["title"]), norm(d["buyer"]))].append(d["doc_id"])
        desc[norm(d.get("description") or "")].append(d["doc_id"])
    bad = dict()
    for q in qs:
        f = []
        gold = q["gold_doc_ids"]
        for g in gold:
            if g not in by_id or g in withheld:
                f.append("gold_not_in_corpus")
        for s in q["gold_spans"]:
            d = by_id.get(s["doc_id"])
            if d is None or s["text"] not in doc_text(d):
                f.append("span_not_in_doc")
        txt = q["text"].lower()
        for k in q["must_keep"]:
            if k.lower() not in txt:
                f.append("must_keep_missing")
        sl = q["slice"]
        if sl == "no-answer":
            wd = by_id[q["meta"]["withheld_doc"]]
            if tb[(norm(wd["title"]), norm(wd["buyer"]))]:
                f.append("na_present_in_corpus")
        elif sl == "paraphrase-heavy":
            d = by_id[gold[0]]
            if len(desc[norm(d.get("description") or "")]) != 1:
                f.append("description_not_unique")
        elif sl in ("factoid-numeric", "factoid-date", "entity", "adversarial-neardup"):
            d = by_id[gold[0]]
            if len(tb[(norm(d["title"]), norm(d["buyer"]))]) != 1 and sl != "adversarial-neardup":
                f.append("title_buyer_not_unique")
            if sl == "adversarial-neardup":
                same = [x for x in tb[(norm(d["title"]), norm(d["buyer"]))] if x != d["doc_id"]]
                for x in same:
                    o = by_id[x]
                    if q["meta"]["disambiguator"] == "supplier" and o["suppliers"] == d["suppliers"]:
                        f.append("neardup_same_supplier")
                    if q["meta"]["disambiguator"] == "date" and o.get("award_date") == d.get("award_date"):
                        f.append("neardup_same_date")
        elif sl == "multi-hop":
            for g in gold:
                d = by_id[g]
                if len(tb[(norm(d["title"]), norm(d["buyer"]))]) != 1:
                    f.append("title_buyer_not_unique")
        if q["answer"] is not None and sl not in ("multi-hop", "no-answer"):
            ev = " ".join(s["text"] for s in q["gold_spans"])
            if sl == "paraphrase-heavy":
                ev = by_id[gold[0]]["buyer"]
            if str(q["answer"]) not in ev and sl != "paraphrase-heavy":
                f.append("answer_not_in_span")
        bad[q["id"]] = sorted(set(f))
    return bad


def load_all():
    qs = []
    for sp in ["train", "dev", "testlock"]:
        qs += read_jsonl(os.path.join(QDIR, sp + ".jsonl"))
    return qs


def cmd_det():
    from harness import load_docs
    docs, wh = load_docs()
    all_docs = read_jsonl(os.path.join(ROOT, "data", "ocds", "documents.jsonl"))
    qs = load_all()
    bad = det_check(qs, all_docs, wh)
    n_bad = sum(1 for v in bad.values() if v)
    codes = defaultdict(int)
    for v in bad.values():
        for c in v:
            codes[c] += 1
    print("deterministic check: %d questions, %d with a failure, codes %s" % (len(qs), n_bad, dict(codes)))
    return bad


def cmd_packets():
    from harness import load_docs, Index, bm25_rank
    docs, wh = load_docs()
    ix = Index(docs)
    qs = load_all()
    r = random.Random(SEED)
    sample = []
    for sl in sorted(set(q["slice"] for q in qs)):
        pool = [q for q in qs if q["slice"] == sl]
        r.shuffle(pool)
        sample += pool[:PER_SLICE]
    ranks = bm25_rank(ix, [q["text"] for q in sample], depth=8)
    rows = []
    for q, rk in zip(sample, ranks):
        groups=q.get("relevance_groups",[[g] for g in q["gold_doc_ids"]])
        gold = list(dict.fromkeys(g for group in groups for g in group))
        others = [d for d, _ in rk if d not in gold][:3 if gold else 5]
        labelled = [(d, "gold") for d in gold] + [(d, "other") for d in others]
        r.shuffle(labelled)
        rows.append(dict(id=q["id"], kind="no-answer" if not gold else "answerable", question=q["text"],
                         proposed_answer=q["answer"],
                         docs=[dict(label="D%d" % (i + 1), text=doc_text(ix.doc_by_id[d])) for i, (d, role) in enumerate(labelled)],
                         claimed=[ "D%d" % (i + 1) for i, (d, role) in enumerate(labelled) if role == "gold"],
                         required_fact_groups=[["D%d"%(i+1) for i,(d,role) in enumerate(labelled) if d in group] for group in groups],
                         _roles=[role for _, role in labelled]))
    meta = [dict(id=x["id"], roles=x.pop("_roles")) for x in rows]
    write_jsonl(os.path.join(ROOT, "results", "audit-sample.jsonl"), meta)
    n = 0
    for i in range(0, len(rows), 40):
        n += 1
        write_jsonl(os.path.join(LLMIO, "audit-in-%03d.jsonl" % n), rows[i:i + 40])
    print("audit packets:", n, "files,", len(rows), "questions")


def cmd_score():
    outs = dict()
    for fn in sorted(os.listdir(LLMIO)):
        if fn.startswith("audit-out-"):
            for r in read_jsonl(os.path.join(LLMIO, fn)):
                outs[r["id"]] = r
    expected=set()
    for fn in sorted(os.listdir(LLMIO)):
        if fn.startswith("audit-in-"):
            expected.update(q["id"] for q in read_jsonl(os.path.join(LLMIO,fn)))
    if len(expected)<150 or set(outs)!=expected:
        raise ValueError("Independent audit requires all >=150 planned judgments, no missing/extra ids")
    if any(any(v not in ("yes","no") for k,v in r.items() if k in ("sufficient","unique","any_answers")) for r in outs.values()):
        raise ValueError("Audit judgment must be explicit yes/no")
    qs = dict((q["id"], q) for q in load_all())
    bad = cmd_det()
    per = defaultdict(lambda: [0, 0])
    rows = []
    for qid, r in outs.items():
        q = qs[qid]
        if q["gold_doc_ids"]:
            noisy = r.get("sufficient") != "yes" or r.get("unique") != "yes"
        else:
            noisy = r.get("any_answers") != "no"
        per[q["slice"]][0] += int(noisy)
        per[q["slice"]][1] += 1
        rows.append(dict(id=qid, slice=q["slice"], noisy=noisy, det=bad.get(qid), reason=r.get("reason", "")[:200]))
    tot_n = sum(v[1] for v in per.values())
    tot_k = sum(v[0] for v in per.values())
    lo, hi = M.wilson(tot_k, tot_n)
    res = dict(n=tot_n, noisy=tot_k, rate=tot_k / max(1, tot_n), wilson95=[lo, hi],
               per_slice=dict((k, dict(noisy=v[0], n=v[1], wilson95=M.wilson(v[0], v[1]))) for k, v in per.items()), rows=rows)
    with open(os.path.join(ROOT, "results", "audit.json"), "w") as f:
        json.dump(res, f, indent=1)
    print("judge noise %d/%d = %.3f  Wilson95 [%.3f, %.3f]" % (tot_k, tot_n, res["rate"], lo, hi))
    for k, v in sorted(per.items()):
        print("  %-22s %d/%d" % (k, v[0], v[1]))


if __name__ == "__main__":
    dict(det=cmd_det, packets=cmd_packets, score=cmd_score)[sys.argv[1]]()
