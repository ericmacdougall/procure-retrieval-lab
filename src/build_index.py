"""Stage build-index: chunk the corpus and cache dense embeddings (resumable shards)."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import load_docs, Index

if __name__ == "__main__":
    t = time.time()
    docs, wh = load_docs()
    ix = Index(docs)
    print("docs", len(docs), "chunks", len(ix.texts), "bm25 built in %.1fs" % (time.time() - t), flush=True)
    ix.emb()
    print("done in %.0fs" % (time.time() - t), flush=True)
