"""Own BM25 (Robertson/Lucene idf) on a sparse term-document matrix. Scores are chunk-level; callers aggregate."""
import os
import sys
import numpy as np
import scipy.sparse as sp

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import tok


class BM25:
    def __init__(self, texts, k1=1.2, b=0.75, stop=None):
        self.stop = stop or set()
        vocab = dict()
        rows, cols, vals = [], [], []
        dl = np.zeros(len(texts), dtype=np.float32)
        for i, t in enumerate(texts):
            counts = dict()
            for w in tok(t):
                if w in self.stop:
                    continue
                counts[w] = counts.get(w, 0) + 1
            dl[i] = sum(counts.values())
            for w, c in counts.items():
                j = vocab.setdefault(w, len(vocab))
                rows.append(i)
                cols.append(j)
                vals.append(c)
        self.vocab = vocab
        self.n = len(texts)
        self.tf = sp.csr_matrix((np.array(vals, dtype=np.float32), (rows, cols)), shape=(self.n, len(vocab)))
        self.dl = dl
        self.avgdl = float(dl.mean()) if self.n else 1.0
        df = np.asarray((self.tf > 0).sum(axis=0)).ravel().astype(np.float32)
        self.idf = np.log(1.0 + (self.n - df + 0.5) / (df + 0.5)).astype(np.float32)
        self.set_params(k1, b)

    def set_params(self, k1, b):
        self.k1, self.b = k1, b
        tf = self.tf.tocoo()
        denom = tf.data + k1 * (1.0 - b + b * self.dl[tf.row] / self.avgdl)
        w = self.idf[tf.col] * tf.data * (k1 + 1.0) / denom
        self.w = sp.csc_matrix((w.astype(np.float32), (tf.row, tf.col)), shape=tf.shape)

    def scores(self, query):
        ids = [self.vocab[w] for w in tok(query) if w in self.vocab and w not in self.stop]
        if not ids:
            return np.zeros(self.n, dtype=np.float32)
        return np.asarray(self.w[:, ids].sum(axis=1)).ravel()
