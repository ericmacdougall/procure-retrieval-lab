"""Shared helpers: paths, jsonl io, hashing, tokenisation, seeds."""
import gzip
import hashlib
import json
import os
import random
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "ocds", "raw")
DOCS = os.path.join(ROOT, "data", "ocds", "documents.jsonl")
QDIR = os.path.join(ROOT, "questions")
HELDOUT_DIR = os.path.join(ROOT, "heldout")
RESULTS = os.path.join(ROOT, "results")
CACHE = os.path.join(ROOT, "cache")
SEED = 20261110

TOKEN_RE = re.compile(r"[a-z0-9]+")


def tok(text):
    return TOKEN_RE.findall(text.lower())


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1048576), b""):
            h.update(blk)
    return h.hexdigest()


def sha256_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def hash_bucket(key, mod=100):
    """Stable bucket of a string key (doc id): used for split assignment."""
    return int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:12], 16) % mod


def read_jsonl(path):
    op = gzip.open if path.endswith(".gz") else open
    out = []
    with op(path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def write_jsonl(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + chr(10))
    os.replace(tmp, path)


def rng(seed, salt=""):
    return random.Random(sha256_text(str(seed) + salt))
