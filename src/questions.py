"""Stage make-questions: template questions with exact gold from structured fields.

Order (pre-registration discipline): the HELD-OUT set is drawn FIRST, stratified by slice, into heldout/.
Then train / dev / test-lock are drawn from the remaining gold documents and assigned by a fixed hash of the
(first) gold document id.  No document is gold for questions in two different partitions.

Slices: factoid-numeric, factoid-date, entity, paraphrase-heavy, multi-hop, no-answer, adversarial-neardup.
"""
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DOCS, QDIR, HELDOUT_DIR, SEED, ROOT, read_jsonl, write_jsonl, rng, sha256_text, hash_bucket, tok, sha256_file
from render import fields, doc_text, money

SLICES = ["factoid-numeric", "factoid-date", "entity", "paraphrase-heavy", "multi-hop", "no-answer", "adversarial-neardup"]
HELDOUT_PER_SLICE = 60
QUOTA = dict(train=100, dev=100, testlock=50)
WITHHOLD_FRAC = 0.03


def norm(s):
    return " ".join(tok(s))


def split_of(doc_id):
    b = hash_bucket(doc_id, 100)
    return "train" if b < 40 else ("dev" if b < 80 else "testlock")


def ev(d, field):
    for _, f, t in fields(d):
        if f == field:
            return dict(doc_id=d["doc_id"], field=field, text=t)
    return None


class Ctx:
    def __init__(self, docs):
        self.docs = docs
        self.by_id = dict((d["doc_id"], d) for d in docs)
        self.cnt_tb = defaultdict(int)
        self.cnt_ts = defaultdict(int)
        self.cnt_desc = defaultdict(int)
        self.groups = defaultdict(list)
        for d in docs:
            d["_tb"] = (norm(d["title"]), norm(d["buyer"]))
            self.cnt_tb[d["_tb"]] += 1
            self.cnt_ts[(d["_tb"], norm("; ".join(d["suppliers"])))] += 1
            self.cnt_desc[norm(d.get("description") or "")] += 1
            gk = (norm(d["buyer"]), re.sub("[0-9]+", "", norm(d["title"])).strip())
            self.groups[gk].append(d["doc_id"])


def single(d):
    return d["n_awards"] == 1 and len(d["suppliers"]) == 1


def mk(slice_, tid, text, gold_docs, answer, atype, must_keep, spans, meta=None):
    gid = "+".join(d["doc_id"] for d in gold_docs) if gold_docs else "none"
    qid = "Q" + sha256_text(slice_ + tid + gid + text)[:10]
    return dict(
        id=qid, text=text, text_template=text, text_paraphrase=None, paraphrase_model=None,
        slice=slice_, template_id=tid, gold_doc_ids=[d["doc_id"] for d in gold_docs], gold_spans=spans,
        answer=answer, answer_type=atype, must_keep=must_keep, meta=meta or dict(),
    )


def gen_factoid_numeric(c, d, r):
    t = r.choice([
        ("fn1", "What was the awarded value of the contract '{T}' from {B}?"),
        ("fn2", "How much was the {T} contract awarded by {B} worth?"),
        ("fn3", "What is the contract value for {T} ({B})?"),
    ])
    text = t[1].format(T=d["title"], B=d["buyer"])
    return mk("factoid-numeric", t[0], text, [d], money(d["currency"], d["amounts"][0]), "money", [d["buyer"]], [ev(d, "value")], dict(amount=d["amounts"][0]))


def gen_factoid_date(c, d, r):
    opts = []
    if d.get("contract_start"):
        opts.append(("fd1", "On what date did the {T} contract for {B} start?", "contract_start"))
    if d.get("contract_end"):
        opts.append(("fd2", "When does the contract '{T}' awarded by {B} end?", "contract_end"))
    if d.get("award_date"):
        opts.append(("fd3", "On what date was the {T} contract from {B} awarded?", "award_date"))
    if not opts:
        return None
    t = r.choice(opts)
    text = t[1].format(T=d["title"], B=d["buyer"])
    return mk("factoid-date", t[0], text, [d], d[t[2]], "date", [d["buyer"]], [ev(d, t[2])], dict(field=t[2]))


def gen_entity(c, d, r):
    if r.random() < 0.6:
        t = r.choice([("en1", "Which supplier won the '{T}' contract from {B}?"), ("en2", "Who was awarded the {T} contract by {B}?")])
        text = t[1].format(T=d["title"], B=d["buyer"])
        return mk("entity", t[0], text, [d], d["suppliers"][0], "entity", [d["buyer"]], [ev(d, "suppliers")])
    if c.cnt_ts[(d["_tb"], norm(d["suppliers"][0]))] != 1:
        return None
    text = "Which organisation bought the {T} contract that was awarded to {S}?".format(T=d["title"], S=d["suppliers"][0])
    return mk("entity", "en3", text, [d], d["buyer"], "entity", [d["suppliers"][0]], [ev(d, "buyer")])


def gen_paraphrase_heavy(c, d, r):
    desc = d.get("description") or ""
    if len(desc.split()) < 12 or c.cnt_desc[norm(desc)] != 1:
        return None
    text = "Which contract notice covers this requirement: " + " ".join(desc.split()[:24])
    return mk("paraphrase-heavy", "ph1", text, [d], d["title"], "notice-title", [], [ev(d, "description")], dict(note="answer identifies the matching notice title, not its buyer"))


def gen_multihop(c, d, r, pool_by_buyer):
    others = [x for x in pool_by_buyer.get(norm(d["buyer"]), []) if x["doc_id"] != d["doc_id"] and x["amounts"][0] != d["amounts"][0]]
    if not others:
        return None
    e = r.choice(others)
    a, b = (d, e) if r.random() < 0.5 else (e, d)
    k = r.choice(["mh1", "mh2", "mh3"])
    A, B, BY = a["title"], b["title"], a["buyer"]
    if k == "mh1":
        text = "Which was awarded a higher value by {BY}: the '{A}' contract or the '{B}' contract?".format(BY=BY, A=A, B=B)
        ans = A if a["amounts"][0] > b["amounts"][0] else B
        spans = [ev(a, "value"), ev(b, "value")]
    elif k == "mh2":
        text = "What is the combined awarded value of the '{A}' and '{B}' contracts from {BY}?".format(BY=BY, A=A, B=B)
        ans = money(a["currency"], a["amounts"][0] + b["amounts"][0])
        spans = [ev(a, "value"), ev(b, "value")]
    else:
        if not (a.get("contract_start") and b.get("contract_start")) or a["contract_start"] == b["contract_start"]:
            return None
        text = "Which of the '{A}' and '{B}' contracts from {BY} started earlier?".format(BY=BY, A=A, B=B)
        ans = A if a["contract_start"] < b["contract_start"] else B
        spans = [ev(a, "contract_start"), ev(b, "contract_start")]
    return mk("multi-hop", k, text, [a, b], ans, "compare", [BY], spans)


def gen_noanswer(c, d, r):
    t = r.choice([
        ("na1", "What was the awarded value of the contract '{T}' from {B}?", "value"),
        ("na2", "Which supplier won the '{T}' contract from {B}?", "suppliers"),
        ("na3", "On what date did the {T} contract for {B} start?", "contract_start"),
    ])
    if t[2] == "contract_start" and not d.get("contract_start"):
        return None
    text = t[1].format(T=d["title"], B=d["buyer"])
    return mk("no-answer", t[0], text, [], None, "none", [d["buyer"]], [], dict(withheld_doc=d["doc_id"], would_ask=t[2]))


def gen_adversarial(c, d, r):
    gk = (norm(d["buyer"]), re.sub("[0-9]+", "", norm(d["title"])).strip())
    sib = [x for x in c.groups[gk] if x != d["doc_id"]]
    if not sib:
        return None
    group_docs = [c.by_id[x] for x in c.groups[gk]]
    same_sup = [x for x in group_docs if x["suppliers"] == d["suppliers"] and x["doc_id"] != d["doc_id"]]
    by = None
    if not same_sup and c.cnt_ts[(d["_tb"], norm(d["suppliers"][0]))] == 1:
        by = "supplier"
    elif d.get("award_date"):
        n = sum(1 for x in group_docs if x["_tb"] == d["_tb"] and x.get("award_date") == d["award_date"])
        if n == 1 and c.cnt_tb[d["_tb"]] == sum(1 for x in group_docs if x["_tb"] == d["_tb"]):
            by = "date"
    if by is None:
        return None
    T, B, S = d["title"], d["buyer"], d["suppliers"][0]
    meta = dict(disambiguator=by, siblings=len(sib))
    if by == "supplier":
        if r.random() < 0.5:
            text = "What was the awarded value of the '{T}' contract from {B} that was awarded to {S}?".format(T=T, B=B, S=S)
            return mk("adversarial-neardup", "ad1s", text, [d], money(d["currency"], d["amounts"][0]), "money", [B, S], [ev(d, "value")], meta)
        if not d.get("contract_start"):
            return None
        text = "On what date did the '{T}' contract from {B} awarded to {S} start?".format(T=T, B=B, S=S)
        return mk("adversarial-neardup", "ad2s", text, [d], d["contract_start"], "date", [B, S], [ev(d, "contract_start")], meta)
    text = "Who was awarded the '{T}' contract by {B} on {D}?".format(T=T, B=B, D=d["award_date"])
    return mk("adversarial-neardup", "ad3d", text, [d], S, "entity", [B, d["award_date"]], [ev(d, "suppliers")], meta)


def candidates(c, docs, uniq, pool_by_buyer, seed):
    cands = dict()
    for sl in SLICES:
        r = rng(seed, "pool-" + sl)
        out = []
        if sl == "no-answer":
            src = sorted([d for d in docs if d["withheld"]], key=lambda d: d["doc_id"])
            r.shuffle(src)
            for d in src:
                q = gen_noanswer(c, d, r)
                if q:
                    out.append(q)
        elif sl == "adversarial-neardup":
            src = sorted([d for d in docs if single(d) and not d["withheld"]], key=lambda d: d["doc_id"])
            r.shuffle(src)
            for d in src:
                q = gen_adversarial(c, d, r)
                if q:
                    out.append(q)
        else:
            order = list(range(len(uniq)))
            r.shuffle(order)
            for i in order:
                d = uniq[i]
                if sl == "factoid-numeric":
                    q = gen_factoid_numeric(c, d, r)
                elif sl == "factoid-date":
                    q = gen_factoid_date(c, d, r)
                elif sl == "entity":
                    q = gen_entity(c, d, r)
                elif sl == "paraphrase-heavy":
                    q = gen_paraphrase_heavy(c, d, r)
                else:
                    q = gen_multihop(c, d, r, pool_by_buyer)
                if q:
                    out.append(q)
                if len(out) >= 4000:
                    break
        cands[sl] = out
    return cands


def gold_ids(q):
    return q["gold_doc_ids"] or [q["meta"]["withheld_doc"]]


def build(docs, seed=SEED, heldout_per_slice=HELDOUT_PER_SLICE, quota=QUOTA):
    c = Ctx(docs)
    elig = [d for d in docs if single(d) and c.cnt_tb[d["_tb"]] == 1]
    rng(seed, "withhold").shuffle(elig)
    withheld = set(d["doc_id"] for d in elig[: int(len(elig) * WITHHOLD_FRAC)])
    for d in docs:
        d["withheld"] = d["doc_id"] in withheld
    uniq = sorted([d for d in elig if not d["withheld"]], key=lambda d: d["doc_id"])
    pool_by_buyer = defaultdict(list)
    for d in uniq:
        pool_by_buyer[norm(d["buyer"])].append(d)
    cands = candidates(c, docs, uniq, pool_by_buyer, seed)
    used = set()
    held = []
    for sl in SLICES:     # HELD-OUT FIRST
        n = 0
        for q in cands[sl]:
            ids = gold_ids(q)
            if any(i in used for i in ids):
                continue
            q["split"] = "heldout"
            held.append(q)
            used.update(ids)
            n += 1
            if n >= heldout_per_slice:
                break
    rest = []
    for sl in SLICES:
        cnt = defaultdict(int)
        for q in cands[sl]:
            ids = gold_ids(q)
            if any(i in used for i in ids) or len(set(split_of(i) for i in ids)) > 1:
                continue
            sp = split_of(ids[0])
            if cnt[sp] >= quota[sp]:
                continue
            q["split"] = sp
            rest.append(q)
            used.update(ids)
            cnt[sp] += 1
    for q in held + rest:
        q["doc_bucket"] = hash_bucket(gold_ids(q)[0], 100)
    return docs, held, rest, cands


def main():
    docs = read_jsonl(DOCS)
    docs, held, rest, cands = build(docs)
    os.makedirs(QDIR, exist_ok=True)
    os.makedirs(HELDOUT_DIR, exist_ok=True)
    hp = os.path.join(HELDOUT_DIR, "questions.template.jsonl")
    import guard; guard.build_write(hp, held)
    h0 = sha256_file(hp)
    for sp in ["train", "dev", "testlock"]:
        write_jsonl(os.path.join(QDIR, sp + ".template.jsonl"), [q for q in rest if q["split"] == sp])
    write_jsonl(os.path.join(ROOT, "data", "docs", "withheld_ids.jsonl"), [dict(doc_id=d["doc_id"]) for d in docs if d["withheld"]])
    stat = defaultdict(lambda: defaultdict(int))
    for q in held + rest:
        stat[q["split"]][q["slice"]] += 1
    summary = dict(
        n_docs=len(docs), n_withheld=sum(1 for d in docs if d["withheld"]), heldout_template_sha256=h0,
        counts=dict((k, dict(v)) for k, v in stat.items()), total=len(held) + len(rest),
        candidate_pool=dict((k, len(v)) for k, v in cands.items()),
    )
    print(json.dumps(summary, indent=1))
    with open(os.path.join(QDIR, "generation-summary.json"), "w") as f:
        json.dump(summary, f, indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
