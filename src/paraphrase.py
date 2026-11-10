"""LLM paraphrase file exchange.  `batches` writes llm-io/paraphrase-in-NNN.jsonl (about 100 questions each);
subagents on the Mac write llm-io/paraphrase-out-NNN.jsonl; `merge` validates and writes the final question files.

The model sees only the template question and the spans that must survive: no gold document id, no answer.
Validation (deterministic): every must_keep span present (case-insensitive), title words kept (>= 70 percent),
no document id or ocid leaked, not identical to the template, 5-60 words, heavy slice: at most one shared
4-gram with the template.  A failed paraphrase falls back to the template text and is counted.
"""
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import QDIR, HELDOUT_DIR, ROOT, read_jsonl, write_jsonl, tok, sha256_file
import guard

LLMIO = os.path.join(ROOT, "llm-io")
SPLITS = ["train", "dev", "testlock"]
BATCH = 100
LEAK = re.compile(r"\bN[0-9a-f]{12}\b|ocds-|\bQ[0-9a-f]{10}\b")
STYLE = dict(
    light="Reword the question naturally, the way a buyer or analyst would type it into a search box. Keep it one sentence.",
    heavy="The question quotes a requirement from a contract notice. Describe the same requirement in clearly different words (synonyms, different structure). Do NOT copy any run of four or more consecutive words from the original. Keep every place name, product name, number and proper noun.",
)


def ngrams(ws, n=4):
    return set(tuple(ws[i:i + n]) for i in range(len(ws) - n + 1))


def proper_name_ngrams(text):
    """Only contiguous capitalized source names, including small connector words.

    Required named entities cannot be paraphrased without changing the reference.
    This exemption never applies to ordinary lowercase requirement wording.
    """
    pattern=r"\b[A-Z][A-Za-z0-9&’'/-]*(?:(?:\s+(?:and|of|for|the|&))?\s+[A-Z][A-Za-z0-9&’'/-]*)+"
    return set().union(*(ngrams(tok(match.group())) for match in re.finditer(pattern,text)))


def title_words(q):
    """Words inside single quotes in the template (the contract title), when present."""
    m = re.findall(r"'([^']+)'", q["text_template"])
    return m


def load_template_rows():
    rows = []
    for sp in SPLITS:
        rows += read_jsonl(os.path.join(QDIR, sp + ".template.jsonl"))
    held_t = os.path.join(HELDOUT_DIR, "questions.template.jsonl")
    ho = read_jsonl(held_t)
    return rows, ho


def batches():
    os.makedirs(LLMIO, exist_ok=True)
    rows, ho = load_template_rows()
    allrows = [("ho", q) for q in ho] + [("q", q) for q in rows]
    names = []
    for kind in ["ho", "q"]:
        part = [q for k, q in allrows if k == kind]
        for i in range(0, len(part), BATCH):
            n = len(names) + 1
            fn = os.path.join(LLMIO, "paraphrase-in-%03d.jsonl" % n)
            out = []
            for q in part[i:i + BATCH]:
                st = "heavy" if q["slice"] == "paraphrase-heavy" else "light"
                out.append(dict(id=q["id"], style=STYLE[st], question=q["text_template"], must_keep=q["must_keep"]))
            write_jsonl(fn, out)
            names.append((fn, kind, len(out)))
    for fn, kind, n in names:
        print(os.path.basename(fn), kind, n)


def validate(q, p):
    why = []
    if not isinstance(p, str) or not p.strip():
        return ["empty"]
    low = p.lower()
    for s in q["must_keep"]:
        if s.lower() not in low:
            why.append("missing:" + s[:30])
    tw = title_words(q)
    for t in tw:
        toks = [w for w in tok(t)]
        if toks:
            keep = sum(1 for w in toks if w in set(tok(p))) / len(toks)
            if keep < 0.7:
                why.append("title_lost")
    if LEAK.search(p):
        why.append("leak")
    if p.strip() == q["text_template"].strip():
        why.append("identical")
    nw = len(p.split())
    if nw < 5 or nw > 60:
        why.append("length")
    if q["slice"] == "paraphrase-heavy":
        copied=ngrams(tok(p)) & ngrams(tok(q["text_template"]))
        copied-=proper_name_ngrams(q["text_template"])
        if len(copied) > 1:
            why.append("copied_4gram")
    return why


def read_outputs():
    out = dict()
    for fn in sorted(os.listdir(LLMIO)):
        if fn.startswith("paraphrase-out-") and fn.endswith(".jsonl"):
            for r in read_jsonl(os.path.join(LLMIO, fn)):
                out[r["id"]] = r
    return out


def merge(model_name="claude-subagent"):
    guard.reopen_for_question_build()
    rows, ho = load_template_rows()
    outs = read_outputs()
    from common import DOCS
    docs=read_jsonl(DOCS)
    by_id={d["doc_id"]:d for d in docs}
    prefix_counts=Counter(" ".join(tok(" ".join((d.get("description") or "").split()[:24]))) for d in docs)
    dropped=[]
    stat = dict(n=0, valid=0, missing=0, reasons=dict())
    final = []
    for q in rows + ho:
        if q["slice"]=="paraphrase-heavy":
            prefix=" ".join(tok(q["text_template"].split(": ",1)[1]))
            if prefix_counts[prefix]>1:
                dropped.append(dict(id=q["id"],split=q["split"],reason="ambiguous_24_word_description_prefix",matching_documents=prefix_counts[prefix]))
                continue
        stat["n"] += 1
        r = outs.get(q["id"])
        q = dict(q)
        if q["slice"]=="paraphrase-heavy":
            q["answer"]=by_id[q["gold_doc_ids"][0]]["title"]
            q["answer_type"]="notice-title"
            q["meta"]=dict(q["meta"],note="answer identifies matching notice title, not buyer; corrected by pre-freeze audit")
        if r is None:
            stat["missing"] += 1
            why = ["no_output"]
        else:
            why = validate(q, r.get("paraphrase"))
        if not why:
            q["text_paraphrase"] = r["paraphrase"].strip()
            q["text"] = q["text_paraphrase"]
            q["paraphrase_model"] = model_name
            q["paraphrase_valid"] = True
            stat["valid"] += 1
        else:
            q["text"] = q["text_template"]
            q["paraphrase_valid"] = False
            q["paraphrase_fail"] = why
            for w in why:
                k = w.split(":")[0]
                stat["reasons"][k] = stat["reasons"].get(k, 0) + 1
        final.append(q)
    kept=[]
    for q in final:
        if q["slice"]=="paraphrase-heavy" and not q["paraphrase_valid"]:
            dropped.append(dict(id=q["id"],split=q["split"],reason="failed_semantic_rewording_validation_after_one_targeted_repair"))
        else:
            kept.append(q)
    final=kept
    if sum(q["split"]=="heldout" for q in final)<400:
        raise ValueError("Question-quality exclusions leave fewer than 400 held-out cases")
    stat["n_final"]=len(final)
    for sp in SPLITS:
        write_jsonl(os.path.join(QDIR, sp + ".jsonl"), [q for q in final if q["split"] == sp])
    guard.build_write(os.path.join(HELDOUT_DIR, "questions.jsonl"), [q for q in final if q["split"] == "heldout"], who="paraphrase.merge")
    with open(os.path.join(QDIR,"frozen-manifest.json"),"w") as f:
        json.dump(dict(heldout_sha256=sha256_file(os.path.join(HELDOUT_DIR,"questions.jsonl")),
                       model=model_name,validation=stat,counts=dict(Counter(q["split"] for q in final)),
                       answerable_heldout=sum(q["split"]=="heldout" and bool(q["gold_doc_ids"]) for q in final),
                       dropped=dropped,
                       limitation="Ambiguous repeated-prefix questions removed before tuning, making the filtered task easier than the raw query mix; known-source generated-query benchmark only."),f,indent=2)
    guard.seal()
    print(json.dumps(stat, indent=1))
    return stat


if __name__ == "__main__":
    if sys.argv[1] == "batches":
        batches()
    elif sys.argv[1] == "merge":
        merge(*sys.argv[2:3])
