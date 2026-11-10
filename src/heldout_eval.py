"""Open the sealed evaluation once after configuration, source and metrics are frozen."""
import datetime
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parent))
import guard
import metrics
from common import ROOT, SEED, sha256_file
from harness import load_docs,evaluate,summarise
from experiment import rank,dump,candidates,primary

ROOT=Path(ROOT)


def pair_summary(qs,first,second):
    a=evaluate(qs,first)[0]
    b=evaluate(qs,second)[0]
    out={}
    groups={"all":[q for q in qs if q["id"] in a]}
    for q in qs:
        if q["id"] in a:
            groups.setdefault(q["slice"],[]).append(q)
    for group,rows in groups.items():
        out[group]={"n":len(rows)}
        for metric in ["recall@1","recall@10","mrr@10","ndcg@10"]:
            x=[a[q["id"]][metric] for q in rows]
            y=[b[q["id"]][metric] for q in rows]
            mean,lo,hi,p=metrics.paired_bootstrap(x,y,10000,SEED)
            out[group][metric]=dict(mean=mean,lo=lo,hi=hi,p_bootstrap=p)
    return out


def main():
    output=ROOT/"results/heldout/results.json"
    qs=guard.load_heldout("heldout_eval.main")
    for q in qs:
        q["query"]=q["text"]
    if len(qs)<400:
        raise RuntimeError("Evaluation requires at least 400 questions including no-answer cases")
    docs,_=load_docs()
    final=json.loads((ROOT/"configs/final.json").read_text())
    ladder=candidates()[:4]+[("final-selected",final["selected"]["config"]),("tool-policy",dict(system="planner"))]
    all_ranks={}
    results={}
    for name,config in ladder:
        ranks,timing=rank(qs,config,docs)
        all_ranks[name]=ranks
        per,top,answerable=evaluate(qs,ranks)
        pos=[s for s,a in zip(top,answerable) if a]
        neg=[s for s,a in zip(top,answerable) if not a]
        results[name]=dict(config=config,timing=timing,n_total=len(qs),n_answerable=len(per),n_no_answer=len(neg),
                           summary=summarise(qs,per),no_answer_auroc=metrics.auroc(pos,neg),
                           per_query=per,top_scores=top,qids=[q["id"] for q in qs],rankings=ranks)
        tau=final["answerability_thresholds"][name]["tau"]
        scores=np.asarray(top)
        labels=np.asarray(answerable,dtype=bool)
        abstain=scores<tau
        true_abstain=int(np.sum(abstain & ~labels))
        count_abstain=int(np.sum(abstain))
        no_answer_n=int(np.sum(~labels))
        results[name]["abstention"]=dict(tau=tau,true_no_answer_abstentions=true_abstain,n_abstentions=count_abstain,
            n_no_answer=no_answer_n,precision=true_abstain/count_abstain if count_abstain else None,
            recall=true_abstain/no_answer_n,recall_wilson95=metrics.wilson(true_abstain,no_answer_n),
            answerable_coverage=float(np.mean(~abstain[labels])),
            note="Threshold selected on dev; no-answer proportion is deliberately balanced by slice, not a production prior")
        if name!="baseline-bm25":
            results[name]["difference_vs_bm25"]=pair_summary(qs,ranks,all_ranks["baseline-bm25"])
        dump(ROOT/"results/heldout"/(name+".json"),results[name])
        print("HELDOUT",name,results[name]["summary"]["all"]["ndcg@10"],flush=True)
    diff=results["final-selected"]["difference_vs_bm25"]
    primary_diff=diff["all"]["ndcg@10"]
    regressions=[s for s,r in diff.items() if s!="all" and r["ndcg@10"]["mean"]<-.05]
    decision=dict(superiority_established=primary_diff["lo"]>0,
                  primary_difference=primary_diff,slice_regressions_over_margin=regressions,
                  deploy_better_retriever=primary_diff["lo"]>0 and not regressions,
                  rule="Publish evidence regardless of superiority; select no further configuration using these outcomes.")
    dump(output,dict(timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                     frozen_receipt_sha256=sha256_file(str(ROOT/"questions/FREEZE")),
                     n_total=len(qs),n_answerable=sum(bool(q["gold_doc_ids"]) for q in qs),
                     decision=decision,systems=results))
    errors=[]
    baseline=results["baseline-bm25"]["per_query"]
    selected=results["final-selected"]["per_query"]
    for q in qs:
        qid=q["id"]
        if qid not in selected:
            continue
        old=baseline[qid]["ndcg@10"]
        new=selected[qid]["ndcg@10"]
        if new<1:
            errors.append(dict(qid=qid,slice=q["slice"],gold=q["gold_doc_ids"],baseline_ndcg10=old,selected_ndcg10=new,
                               category="candidate_miss" if new==0 else "ranking_or_multi_document_coverage",
                               gold_ranks=[next((i+1 for i,(d,_) in enumerate(all_ranks["final-selected"][qs.index(q)]) if d==g),None) for g in q["gold_doc_ids"]]))
    dump(ROOT/"results/heldout/errors.json",dict(note="Automatic retrieval-error categories; no claim of manual causal diagnosis",n=len(errors),cases=errors[:100]))
    print("DECISION",decision,flush=True)


if __name__=="__main__":
    main()
