"""Common evaluation harness: build index -> rank -> metrics.  Systems: bm25, dense, hybrid, rerank.

Usage: python src/harness.py --system bm25 --split dev [--text final|template] [--limit N] [--tag NAME]
Held-out is never loaded here (see guard.py); only train / dev / testlock splits are accepted.
"""
import argparse
import json
import os
import sys
import time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DOCS, QDIR, RESULTS, ROOT, SEED, read_jsonl, write_jsonl, tok
import metrics as M
from chunking import build_chunks
from bm25 import BM25
import fusion

SPLITS = ("train", "dev", "testlock")
DEFAULT = dict(
    chunk=dict(mode="plain", size=128, overlap=32, prefix_title=True),
    bm25=dict(k1=1.2, b=0.75), depth=100, chunk_depth=300,
    dense=dict(model="BAAI/bge-small-en-v1.5"),
    rrf_k=60, rerank_n=20, rewrite=False,
)


def load_docs():
    docs = read_jsonl(DOCS)
    wh = set(r["doc_id"] for r in read_jsonl(os.path.join(ROOT, "data", "docs", "withheld_ids.jsonl")))
    return [d for d in docs if d["doc_id"] not in wh], wh


def load_questions(split, text="final", limit=None):
    assert split in SPLITS, "held-out is only reachable through the guard module after FREEZE"
    qs = read_jsonl(os.path.join(QDIR, split + (".jsonl" if os.path.exists(os.path.join(QDIR, split + ".jsonl")) else ".template.jsonl")))
    for q in qs:
        q["query"] = q["text_template"] if text == "template" else (q.get("text") or q["text_template"])
    return qs[:limit] if limit else qs


class Index:
    def __init__(self, docs, chunk=None, bm25=None):
        self.cfg = dict(DEFAULT["chunk"])
        self.cfg.update(chunk or dict())
        self.docs = docs
        self.doc_by_id = dict((d["doc_id"], d) for d in docs)
        self.texts, self.cdoc, self.groups = build_chunks(docs, **self.cfg)
        self.cdoc_arr = np.array(self.cdoc)
        p = dict(DEFAULT["bm25"])
        p.update(bm25 or dict())
        self.bm = BM25(self.texts, **p)
        self._emb = None

    def tag(self):
        c = self.cfg
        return "%s_%d_%d_%d_%d" % (c["mode"], c["size"], c["overlap"], int(c["prefix_title"]), len(self.docs))

    def emb(self):
        if self._emb is None:
            import dense
            self._emb = dense.corpus_embeddings(self.texts, self.tag())
        return self._emb

    def to_docs(self, idx, scores, depth):
        seen = dict()
        for i, s in zip(idx, scores):
            d = self.cdoc[i]
            if d not in seen:
                seen[d] = float(s)
                if len(seen) >= depth:
                    break
        return list(seen.items())


def bm25_rank(ix, queries, depth=100, chunk_depth=300):
    out = []
    for q in queries:
        s = ix.bm.scores(q)
        k = min(chunk_depth, len(s))
        part = np.argpartition(-s, k - 1)[:k]
        part = part[np.argsort(-s[part])]
        out.append(ix.to_docs(part, s[part], depth))
    return out


def dense_rank(ix, queries, depth=100, chunk_depth=300):
    import dense
    qe = dense.encode_texts(queries, prefix=dense.QPREFIX)
    idx, sc = dense.search(qe, ix.emb(), chunk_depth)
    return [ix.to_docs(idx[i], sc[i], depth) for i in range(len(queries))]


def run_system(system, ix, queries, cfg=None):
    c = dict(DEFAULT)
    c.update(cfg or dict())
    d, cd = c["depth"], c["chunk_depth"]
    if system == "bm25":
        return bm25_rank(ix, queries, d, cd)
    if system == "dense":
        return dense_rank(ix, queries, d, cd)
    bm = bm25_rank(ix, queries, d, cd)
    de = dense_rank(ix, queries, d, cd)
    if system in ("hybrid", "rerank"):
        fused = [fusion.rrf([a, b], k=c["rrf_k"]) for a, b in zip(bm, de)]
        if system == "hybrid":
            return fused
        import rerank
        return [rerank.rerank(q, f, ix.doc_by_id, n=c["rerank_n"]) for q, f in zip(queries, fused)]
    raise ValueError(system)


def validate_rankings(qs,rankings,corpus_ids=None):
    if len(qs)!=len(rankings):
        raise ValueError("question/ranking length mismatch")
    if len({q["id"] for q in qs})!=len(qs):
        raise ValueError("question ids must be unique")
    for q,ranking in zip(qs,rankings):
        ids=[row[0] for row in ranking]
        if len(ids)!=len(set(ids)):
            raise ValueError("ranked document ids must be unique")
        if any(not np.isfinite(float(row[1])) for row in ranking):
            raise ValueError("ranked scores must be finite")
        if len(q["gold_doc_ids"])!=len(set(q["gold_doc_ids"])):
            raise ValueError("gold document ids must be unique")
        groups=q.get("relevance_groups",[[g] for g in q["gold_doc_ids"]])
        if len(groups)!=len(q["gold_doc_ids"]) or any(not g for g in groups):
            raise ValueError("Each required source must have one nonempty equivalence group")
        members=[x for group in groups for x in group]
        if len(members)!=len(set(members)):
            raise ValueError("Equivalence groups must be disjoint")
        if corpus_ids is not None:
            if not (set(ids)|set(q["gold_doc_ids"])|set(members)).issubset(corpus_ids):
                raise ValueError("ranked/gold document missing from corpus")


def evaluate(qs, rankings):
    """Per-query metrics for answerable questions + top scores for abstention analysis."""
    validate_rankings(qs,rankings)
    per = dict()
    top = []
    ans = []
    for q, r in zip(qs, rankings):
        ids = [x[0] for x in r]
        groups=q.get("relevance_groups",[[g] for g in q["gold_doc_ids"]])
        mapping={member:gold for gold,group in zip(q["gold_doc_ids"],groups) for member in group}
        # One equivalent notice can satisfy its fact group, but redundant aliases never earn extra credit.
        ids=list(dict.fromkeys(mapping.get(doc_id,doc_id) for doc_id in ids))
        top.append(r[0][1] if r else 0.0)
        gold = q["gold_doc_ids"]
        ans.append(bool(gold))
        if gold:
            per[q["id"]] = M.per_query(ids, gold)
    return per, top, ans


def summarise(qs, per, seed=SEED):
    out = dict()
    names = ["recall@1", "recall@5", "recall@10", "recall@20", "mrr@10", "ndcg@10"]
    groups = dict(all=[q for q in qs if q["id"] in per])
    for q in qs:
        if q["id"] in per:
            groups.setdefault(q["slice"], []).append(q)
    for g, lst in groups.items():
        row = dict(n=len(lst))
        for m in names:
            v = [per[q["id"]][m] for q in lst]
            mean, lo, hi = M.bootstrap_ci(v, 10000, seed)
            row[m] = dict(mean=mean, lo=lo, hi=hi)
        h = sum(1 for q in lst if per[q["id"]]["recall@10"] == 1.0)
        row["hit@10_wilson"] = M.wilson(h, len(lst))
        out[g] = row
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--system", required=True)
    ap.add_argument("--split", default="dev")
    ap.add_argument("--text", default="final")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--tag", default=None)
    ap.add_argument("--rewrite", action="store_true")
    ap.add_argument("--quick", action="store_true", help="150 dev questions over their gold docs plus 2000 random docs")
    a = ap.parse_args()
    t0 = time.time()
    docs, wh = load_docs()
    qs = load_questions(a.split, a.text, 150 if a.quick else a.limit)
    if a.quick:
        import random
        need = set(i for q in qs for i in q["gold_doc_ids"])
        rest = [d for d in docs if d["doc_id"] not in need]
        random.Random(SEED).shuffle(rest)
        docs = [d for d in docs if d["doc_id"] in need] + rest[:2000]
        a.tag = (a.tag or a.system) + "_quick"
    ix = Index(docs)
    t_index = time.time() - t0
    queries = [q["query"] for q in qs]
    if a.rewrite:
        from rewrite import rewrite
        queries = [rewrite(x) for x in queries]
    t1 = time.time()
    rk = run_system(a.system, ix, queries)
    dt = time.time() - t1
    per, top, ans = evaluate(qs, rk)
    summ = summarise(qs, per)
    res = dict(system=a.system, split=a.split, text=a.text, n_questions=len(qs), n_docs=len(docs), seed=SEED,
               config=DEFAULT, index_seconds=t_index, query_seconds_total=dt, ms_per_query=1000 * dt / len(qs), summary=summ,
               per_query=per, top_scores=top, answerable=ans, qids=[q["id"] for q in qs], rewrite=a.rewrite)
    os.makedirs(RESULTS, exist_ok=True)
    fn = os.path.join(RESULTS, "%s_%s_%s%s.json" % (a.tag or a.system, a.split, a.text, "_rw" if a.rewrite else ""))
    with open(fn, "w") as f:
        json.dump(res, f)
    s = summ["all"]
    print("%s %s n=%d (answerable %d)  R@1 %.3f  R@10 %.3f [%.3f,%.3f]  MRR@10 %.3f  nDCG@10 %.3f  %.1f ms/q -> %s" % (
        a.system, a.split, len(qs), s["n"], s["recall@1"]["mean"], s["recall@10"]["mean"], s["recall@10"]["lo"], s["recall@10"]["hi"],
        s["mrr@10"]["mean"], s["ndcg@10"]["mean"], res["ms_per_query"], fn))


if __name__ == "__main__":
    main()
