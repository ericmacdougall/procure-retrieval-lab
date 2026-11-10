"""Chunking: plain sliding word windows over the whole rendered document, or field-aware groups.

A chunk is (chunk_id, doc_id, group, text).  The doc-to-chunk map is chunk_doc (list of doc ids, aligned).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import fields, doc_text


def windows(words, size, overlap):
    if len(words) <= size:
        return [words]
    step = max(1, size - overlap)
    out = []
    i = 0
    while True:
        out.append(words[i:i + size])
        if i + size >= len(words):
            break
        i += step
    return out


def chunk_doc(d, mode="plain", size=128, overlap=32, prefix_title=True):
    """mode plain: windows over the full text.  mode field: one chunk per field group (head, body, terms);
    long bodies are windowed; body and terms chunks carry the title as a context prefix when prefix_title."""
    if mode == "plain":
        ws = doc_text(d).split()
        return [("all", " ".join(w)) for w in windows(ws, size, overlap)]
    groups = dict()
    order = []
    for g, _, t in fields(d):
        if g not in groups:
            groups[g] = []
            order.append(g)
        groups[g].append(t)
    out = []
    for g in order:
        text = " ".join(groups[g])
        if g == "head":
            out.append((g, text))
            continue
        pre = ("Title: " + d["title"] + ". ") if prefix_title else ""
        ws = text.split()
        for w in windows(ws, size, overlap):
            out.append((g, pre + " ".join(w)))
    return out


def build_chunks(docs, mode="plain", size=128, overlap=32, prefix_title=True):
    texts = []
    cdoc = []
    groups = []
    for d in docs:
        for g, t in chunk_doc(d, mode, size, overlap, prefix_title):
            texts.append(t)
            cdoc.append(d["doc_id"])
            groups.append(g)
    return texts, cdoc, groups
