"""Development-only retrieval experiment. The sealed evaluation has a separate entry point."""
import argparse
import copy
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, CACHE, SEED, sha256_file, read_jsonl
from harness import Index, load_docs, load_questions, evaluate, summarise, bm25_rank, dense_rank, DEFAULT,validate_rankings
import fusion
import metrics

ROOT = Path(ROOT)
MEMORY = {}


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temp.replace(path)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def primary(qs, rankings):
    per, _, _ = evaluate(qs, rankings)
    return float(np.mean([v["ndcg@10"] for v in per.values()]))


def rerank_many(queries, rankings, docs, n):
    """Score all pairs together, rather than repeatedly initializing tiny batches."""
    from rerank import ce
    from render import doc_text
    head = [r[:n] for r in rankings]
    pairs = [(q, doc_text(docs[d])) for q, row in zip(queries, head) for d, _ in row]
    scores = ce().predict(pairs, batch_size=64, show_progress_bar=False)
    output, offset = [], 0
    for row, rest in zip(head, rankings):
        values = np.asarray(scores[offset:offset+len(row)])
        offset += len(row)
        order = np.argsort(-values, kind="stable")
        result = [(row[i][0], float(values[i])) for i in order]
        floor = float(values.min()) - 1 if len(values) else -1
        result += [(d, floor-j*1e-6) for j, (d, _) in enumerate(rest[n:])]
        output.append(result)
    return output


def rank(qs, config, docs):
    # A component cache must ignore settings belonging to later fusion/rerank stages.
    if config["system"] in ("bm25", "dense"):
        keep={"system","chunk","chunk_depth","rewrite"}
        if config["system"]=="bm25":
            keep |= {"k1","b"}
        config={k:v for k,v in config.items() if k in keep}
    source = sha256_file(str(ROOT / "data/ocds/documents.jsonl"))
    source_code = {p.name: sha256_file(str(p)) for p in (ROOT / "src").glob("*.py")}
    import dense,rerank
    runtime=dict(dense_revision=dense.REVISION,dense_maxlen=dense.MAXLEN,reranker_revision=rerank.REVISION,
                 threads=int(os.getenv("AX11_THREADS","6")))
    queries = [q["query"] for q in qs]
    if config.get("rewrite"):
        from rewrite import rewrite
        queries = [rewrite(x) for x in queries]
    key = digest(dict(config=config, queries=queries, source=source, code=source_code,runtime=runtime,
                     withheld=sha256_file(str(ROOT/"data/docs/withheld_ids.jsonl"))))
    cached = ROOT / "cache/rankings" / (key + ".json")
    if cached.exists():
        prior=json.loads(cached.read_text())
        validate_rankings(qs,prior["rankings"],{d["doc_id"] for d in docs})
        return prior["rankings"], dict(cached=True, seconds=prior["seconds"], cache_key=key,
                                      note="Seconds from the original measured run; this cache access was not benchmarked")
    chunk = config.get("chunk", DEFAULT["chunk"])
    index_key = digest(chunk)
    if index_key not in MEMORY:
        MEMORY[index_key] = Index(docs, chunk=chunk)
    ix = MEMORY[index_key]
    ix.bm.set_params(config.get("k1", 1.2), config.get("b", .75))
    start = time.perf_counter()
    depth = config.get("chunk_depth", 300)
    system = config["system"]
    if system == "bm25":
        ranks = bm25_rank(ix, queries, 100, depth)
    elif system == "dense":
        ranks = dense_rank(ix, queries, 100, depth)
    elif system=="planner":
        from tool_policy import ToolPolicy
        fallback,_=rank(qs,dict(system="hybrid"),docs)
        ranks,routes=ToolPolicy(docs).run(queries,fallback)
    else:
        # Reuse separately recorded components for the fusion ablation.
        base = dict(config, system="bm25")
        bm, _ = rank(qs, base, docs)
        de, _ = rank(qs, dict(config, system="dense"), docs)
        if config.get("fusion") == "weighted":
            weight = config.get("weight", .5)
            ranks = [fusion.weighted([b, d], [weight, 1-weight]) for b, d in zip(bm, de)]
        else:
            ranks = [fusion.rrf([b, d], k=config.get("rrf_k", 60)) for b, d in zip(bm, de)]
        if system == "rerank":
            ranks = rerank_many(queries, ranks, ix.doc_by_id, config.get("rerank_n", 20))
        elif system != "hybrid":
            raise ValueError("Unknown system: " + system)
    seconds = time.perf_counter() - start
    validate_rankings(qs,ranks,{d["doc_id"] for d in docs})
    dump(cached, dict(rankings=ranks, seconds=seconds, config=config,
                     hardware=dict(cpu_count=os.cpu_count(),cpu_affinity=len(os.sched_getaffinity(0)),
                                   threads=int(os.getenv("AX11_THREADS","6")),loadavg=os.getloadavg(),platform=platform.platform()),
                     workload=dict(n_queries=len(qs),n_documents=len(docs),n_chunks=len(ix.texts))))
    return ranks, dict(cached=False, seconds=seconds, cache_key=key)


def candidates():
    configs = [("baseline-bm25", dict(system="bm25")), ("baseline-dense", dict(system="dense")),
               ("baseline-hybrid", dict(system="hybrid")), ("baseline-rerank", dict(system="rerank", rerank_n=20))]
    for k1, b in [(.6,.75),(2.,.75),(1.2,0.),(1.2,.5),(1.2,1.)]:
        configs.append((f"bm25-k{k1}-b{b}", dict(system="bm25", k1=k1, b=b)))
    for mode, size, overlap in [("plain",64,16),("plain",256,64),("field",128,32)]:
        configs.append((f"chunk-{mode}-{size}", dict(system="bm25", chunk=dict(mode=mode,size=size,overlap=overlap,prefix_title=True))))
    configs += [(f"rrf-{k}", dict(system="hybrid", rrf_k=k)) for k in (10,120)]
    configs += [(f"weight-{w}", dict(system="hybrid", fusion="weighted", weight=w)) for w in (.25,.5,.75)]
    configs += [(f"rerank-{n}", dict(system="rerank", rerank_n=n)) for n in (5,10)]
    configs += [("rewrite-bm25", dict(system="bm25", rewrite=True)),
                ("rewrite-hybrid", dict(system="hybrid", rewrite=True)),
                ("depth-100", dict(system="hybrid", chunk_depth=100))]
    return configs


def preregister():
    if (ROOT / "PREREG.md").exists():
        return
    manifest=json.loads((ROOT / "questions/frozen-manifest.json").read_text())
    policy = dict(version=1, timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  seed=SEED, total_n=manifest["counts"]["heldout"], answerable_n=manifest["answerable_heldout"],
                  no_answer_n=manifest["counts"]["heldout"]-manifest["answerable_heldout"],
                  primary="nDCG@10 on answerable required fact groups, equivalent notice versions collapsed in ranks and gold", bootstrap=10000,
                  baseline="baseline-bm25", superiority_rule="paired 95% bootstrap CI lower bound > 0",
                  slice_regression_margin=.05,
                  scope="Anchor-document-disjoint generated queries over a fixed known procurement corpus. Equivalent source versions, buyers and contract families can overlap across partitions; no new-buyer or human-user generalization claim. Query-level intervals may be optimistic under family dependence.",
                  candidate_budget=len(candidates()), configs=candidates(),
                  additional_arm="Rule-based structured-tool routing over the same registry, compared separately for ax02, never an LLM planner claim",
                  no_answer_policy="Threshold chosen on development top-score balanced answerability accuracy; frozen and evaluated separately on no-answer cases",
                  small_benchmark_demo="Choose best declared configuration on twelve stratified answerable test-lock questions (two per slice), compare on remaining test-lock questions. This intentional misuse is separate from dev-only final selection.",
                  question_hashes={str(p.relative_to(ROOT)):sha256_file(str(p)) for p in (ROOT / "questions").glob("*.jsonl")},
                  heldout_hash=manifest["heldout_sha256"],filtering_limitation=manifest["limitation"],dropped_questions=manifest["dropped"],
                  corpus_hash=sha256_file(str(ROOT / "data/ocds/documents.jsonl")),
                  selection="Highest dev nDCG@10 among declared configurations; ties prefer earlier candidate. Heldout outcome never changes selection.",
                  nonpositive_result="A failure to establish superiority is a valid experiment result, never a reason to retune against heldout.")
    text = "# Pre-registration\n\nFixed before any tuning or sealed evaluation.\n\n```json\n" + json.dumps(policy,indent=2) + "\n```\n"
    (ROOT / "PREREG.md").write_text(text)
    with (ROOT / "logs/runlog.jsonl").open("a") as f:
        f.write(json.dumps(dict(event="preregister", sha256=sha256_file(str(ROOT / "PREREG.md")), timestamp=policy["timestamp"]))+"\n")
    print("PREREG", sha256_file(str(ROOT / "PREREG.md")), flush=True)


def tune():
    if (ROOT / "questions/FREEZE").exists():
        raise RuntimeError("Experiment frozen. Tuning requires a new experiment and fresh evaluation data.")
    preregister()
    docs, _ = load_docs()
    qs = load_questions("dev")
    if any(not q.get("paraphrase_valid") for q in qs if q["slice"]=="paraphrase-heavy"):
        raise RuntimeError("Heavy paraphrase slice contains fallback templates; repair before tuning")
    rows=[]
    for name, config in candidates():
        ranks, timing=rank(qs, config, docs)
        score=primary(qs,ranks)
        row=dict(name=name,config=config,ndcg10=score,timing=timing)
        rows.append(row)
        dump(ROOT / "results/dev" / (name+".json"), dict(**row,n=len(qs),summary=summarise(qs,evaluate(qs,ranks)[0])))
        with (ROOT / "logs/runlog.jsonl").open("a") as f:
            f.write(json.dumps(dict(event="dev-run",timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),**row))+"\n")
        print(name,round(score,5),timing,flush=True)
    winner=max(rows,key=lambda r:r["ndcg10"])
    thresholds={}
    for name,config in candidates()[:4]+[("final-selected",winner["config"]),("tool-policy",dict(system="planner"))]:
        ranks,timing=rank(qs,config,docs)
        _,top,answerable=evaluate(qs,ranks)
        scores=np.asarray(top)
        labels=np.asarray(answerable,dtype=bool)
        options=np.unique(np.r_[scores,scores.max()+1e-6])
        def balanced(t):
            decision=scores>=t
            return .5*(np.mean(decision[labels])+np.mean(~decision[~labels]))
        tau=max(options,key=balanced)
        thresholds[name]=dict(tau=float(tau),dev_balanced_accuracy=float(balanced(tau)))
        if name=="tool-policy":
            dump(ROOT/"results/dev/tool-policy.json",dict(summary=summarise(qs,evaluate(qs,ranks)[0]),timing=timing))
    dump(ROOT / "configs/final.json",dict(selected=winner,candidates=rows,primary="ndcg@10",n_dev=len(qs),answerability_thresholds=thresholds))
    print("SELECTED",winner["name"],winner["ndcg10"],flush=True)


def small_benchmark_demo():
    docs,_=load_docs()
    qs=load_questions("testlock")
    small=[]
    for slice_name in sorted({q["slice"] for q in qs if q["gold_doc_ids"]}):
        small+=sorted([q for q in qs if q["slice"]==slice_name],key=lambda q:q["id"])[:2]
    small_ids={q["id"] for q in small}
    fresh=[q for q in qs if q["id"] not in small_ids]
    rows=[]
    ranks_by_name={}
    for name,config in candidates():
        ranks,_=rank(qs,config,docs)
        per=evaluate(qs,ranks)[0]
        small_values=[per[q["id"]]["ndcg@10"] for q in small]
        fresh_values=[per[q["id"]]["ndcg@10"] for q in fresh if q["id"] in per]
        rows.append(dict(name=name,small=metrics.bootstrap_ci(small_values,10000,SEED),fresh=metrics.bootstrap_ci(fresh_values,10000,SEED)))
        ranks_by_name[name]=ranks
    winner=max(rows,key=lambda r:r["small"][0])
    proper=json.loads((ROOT/"configs/final.json").read_text())["selected"]["name"]
    dump(ROOT/"results/ax11/small-benchmark.json",dict(n_selected_on=len(small),n_fresh_answerable=sum(bool(q["gold_doc_ids"]) for q in fresh),
         candidate_count=len(rows),winner=winner,dev_selected=next(r for r in rows if r["name"]==proper),all_candidates=rows,
         selection_optimism=winner["small"][0]-winner["fresh"][0],
         warning="The interval on the maximized twelve-question score is post-selection and not a valid confidence interval for the chosen model's generalization. The fresh set is disjoint; a difference also includes sampling variation."))
    print("SMALL-BENCHMARK",winner,flush=True)


def freeze():
    import guard
    guard.freeze_experiment()


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("stage",choices=["preregister","tune","freeze","small-benchmark"])
    args=parser.parse_args()
    {"preregister":preregister,"tune":tune,"freeze":freeze,"small-benchmark":small_benchmark_demo}[args.stage]()
