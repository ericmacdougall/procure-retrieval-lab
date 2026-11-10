"""Cross-encoder reranker over the top-N documents (scored on the document text, truncated)."""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import doc_text

RERANKER = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_m = dict()


def ce(name=RERANKER):
    if name not in _m:
        import torch
        from sentence_transformers import CrossEncoder
        torch.set_num_threads(int(os.environ.get("AX11_THREADS", "48")))
        _m[name] = CrossEncoder(name, device="cpu", max_length=256)
    return _m[name]


def rerank(query, cand, doc_by_id, n=20, name=RERANKER, batch=64):
    """cand: ranked [(doc_id, score)]. Reranks the first n, keeps the tail order. Returns [(doc_id, ce_score)]
    with the reranked head first (tail scores are pushed below the head so top-score stays the head's)."""
    head = cand[:n]
    if not head:
        return cand
    pairs = [(query, doc_text(doc_by_id[d])) for d, _ in head]
    sc = ce(name).predict(pairs, batch_size=batch, show_progress_bar=False)
    order = np.argsort(-np.asarray(sc))
    out = [(head[i][0], float(sc[i])) for i in order]
    floor = min(float(x) for x in sc) - 1.0
    out += [(d, floor - j * 1e-6) for j, (d, _) in enumerate(cand[n:])]
    return out
