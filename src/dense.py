"""Dense retrieval: local open-weight sentence embeddings, cached on disk in resumable shards, numpy matmul search."""
import hashlib
import os
import sys
import time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import CACHE

MODEL = "BAAI/bge-small-en-v1.5"
QPREFIX = "Represent this sentence for searching relevant passages: "
MAXLEN = int(os.environ.get("AX11_MAXLEN", "192"))
SHARD = 2048
_models = dict()


def model(name=MODEL):
    if name not in _models:
        import torch
        from sentence_transformers import SentenceTransformer
        torch.set_num_threads(int(os.environ.get("AX11_THREADS", "16")))
        _models[name] = SentenceTransformer(name, device="cpu")
        _models[name].max_seq_length = MAXLEN
    return _models[name]


def encode_texts(texts, name=MODEL, batch=64, prefix=""):
    m = model(name)
    order = np.argsort([len(t) for t in texts])
    out = np.zeros((len(texts), m.get_sentence_embedding_dimension()), dtype=np.float32)
    for s in range(0, len(texts), batch * 8):
        idx = order[s:s + batch * 8]
        emb = m.encode([prefix + texts[i] for i in idx], batch_size=batch, normalize_embeddings=True, show_progress_bar=False)
        out[idx] = emb
    return out


def corpus_embeddings(texts, tag, name=MODEL):
    """Cache key = model + maxlen + hash of the texts.  Shards make an interrupted encode resumable."""
    h = hashlib.sha256((name + str(MAXLEN) + chr(10).join(texts)).encode("utf-8")).hexdigest()[:16]
    os.makedirs(CACHE, exist_ok=True)
    fn = os.path.join(CACHE, "emb_%s_%s.npy" % (tag, h))
    if os.path.exists(fn):
        return np.load(fn)
    t0 = time.time()
    parts = []
    done = 0
    for s in range(0, len(texts), SHARD):
        sh = os.path.join(CACHE, "shard_%s_%s_%06d.npy" % (tag, h, s))
        if os.path.exists(sh):
            parts.append(np.load(sh))
        else:
            e = encode_texts(texts[s:s + SHARD], name)
            np.save(sh, e)
            parts.append(e)
            done += len(e)
            el = time.time() - t0
            print("shard %d/%d  %.1f chunks/s  elapsed %.0fs" % (s // SHARD + 1, (len(texts) + SHARD - 1) // SHARD, done / el, el), flush=True)
    e = np.concatenate(parts)
    np.save(fn, e)
    for s in range(0, len(texts), SHARD):
        p = os.path.join(CACHE, "shard_%s_%s_%06d.npy" % (tag, h, s))
        if os.path.exists(p):
            os.remove(p)
    print("encoded %d chunks in %.1fs -> %s" % (len(texts), time.time() - t0, os.path.basename(fn)), flush=True)
    return e


def search(qemb, cemb, k=200):
    s = qemb @ cemb.T
    k = min(k, s.shape[1])
    part = np.argpartition(-s, k - 1, axis=1)[:, :k]
    ps = np.take_along_axis(s, part, axis=1)
    o = np.argsort(-ps, axis=1)
    return np.take_along_axis(part, o, axis=1), np.take_along_axis(ps, o, axis=1)
