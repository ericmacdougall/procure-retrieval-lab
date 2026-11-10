"""Render human-readable results from observed experiment artifacts, with no model calls."""
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import ROOT
from experiment import dump

ROOT=Path(ROOT)


def cell(metric):
    return f'{metric["mean"]:.4f} [{metric["lo"]:.4f}, {metric["hi"]:.4f}]'


def main():
    data=json.loads((ROOT/"results/heldout/results.json").read_text())
    config=json.loads((ROOT/"configs/final.json").read_text())
    manifest=json.loads((ROOT/"questions/frozen-manifest.json").read_text())
    rows=["# Procurement retrieval lab: observed results","", 
          "These are generated, paraphrased queries over real public UK procurement notices. The corpus is fixed and known to every retriever. Gold-document splits are disjoint; buyers and related contract families can recur across partitions. This establishes performance for this filtered benchmark, not production user-query quality or unseen-buyer generalization.","",
          f'The held-out set contains **{data["n_total"]} questions**, of which **{data["n_answerable"]} are answerable**. No-answer questions have a separate abstention evaluation and do not inflate the retrieval denominator.',"",
          "Intervals below use ten thousand paired bootstrap resamples for differences, and ordinary query bootstrap intervals for individual means. These are conditional on this corpus and question-generation process; contract-family dependence may make query-level intervals optimistic. Slices are exploratory and not multiplicity-adjusted.","",
          "| System | nDCG@10 (95% CI) | Recall@10 (95% CI) | MRR@10 (95% CI) | Difference in nDCG vs BM25 |","|---|---|---|---|---|"]
    bars=[]
    for i,(name,res) in enumerate(data["systems"].items()):
        summary=res["summary"]["all"]
        delta=cell(res["difference_vs_bm25"]["all"]["ndcg@10"]) if "difference_vs_bm25" in res else "reference"
        rows.append(f'| {name} | {cell(summary["ndcg@10"])} | {cell(summary["recall@10"])} | {cell(summary["mrr@10"])} | {delta} |')
        bars.append(f'<text x="5" y="{35+i*38}" font-size="13">{name}</text><rect x="155" y="{20+i*38}" width="{summary["ndcg@10"]["mean"]*400:.1f}" height="22" fill="#335b9a"/><text x="{165+summary["ndcg@10"]["mean"]*400:.1f}" y="{36+i*38}" font-size="12">{summary["ndcg@10"]["mean"]:.3f}</text>')
    rows += ["","## Pre-registered decision","",f'Development selected `{config["selected"]["name"]}` from {len(config["candidates"])} declared configurations. The observed held-out decision is:',"","```json",json.dumps(data["decision"],indent=2),"```","",
             "A nonpositive or uncertain result is reported without choosing another configuration on the held-out outcomes. The structured-tool policy is a separate deterministic routing arm; it is not a language-model planner.","","## No-answer behavior","",
             "The threshold was calibrated on development questions, maximizing balanced answerability accuracy. The deliberately balanced slice mix is not a production prior; reported abstention precision will change with prevalence.","",
             "| System | Abstention precision | No-answer recall | Answerable coverage |","|---|---|---|---|"]
    for name,res in data["systems"].items():
        a=res["abstention"]
        precision=f'{a["precision"]:.4f}' if a["precision"] is not None else "undefined: no abstentions"
        rows.append(f'| {name} | {precision} | {a["recall"]:.4f} | {a["answerable_coverage"]:.4f} |')
    rows += ["","## Slice results","","| System and slice | n | nDCG@10 with 95% CI |","|---|---|---|"]
    for name,res in data["systems"].items():
        for group,summary in res["summary"].items():
            if group!="all":
                rows.append(f'| {name}: {group} | {summary["n"]} | {cell(summary["ndcg@10"])} |')
    demo_path=ROOT/"results/ax11/small-benchmark.json"
    if demo_path.exists():
        demo=json.loads(demo_path.read_text())
        rows += ["","## The twelve-question selection trap","",f'A separate demonstration selected `{demo["winner"]["name"]}` by maximizing nDCG on {demo["n_selected_on"]} test-lock questions. Its selected-on score was {demo["winner"]["small"][0]:.4f}; on the remaining {demo["n_fresh_answerable"]} answerable test-lock questions it was {demo["winner"]["fresh"][0]:.4f}. The observed difference was {demo["selection_optimism"]:.4f}. This contrast includes sample composition and sampling variation; it does not by itself identify a causal amount of selection bias.',"",demo["warning"]]
    rows += ["","## Label quality and task scope","",manifest["limitation"],"",f'{len(manifest["dropped"])} ambiguous-prefix questions were removed before tuning. Full exclusions and split counts are in `questions/frozen-manifest.json`. The remaining labels still require the independent sample audit in `results/audit.json`.',"",
             "## What is and is not measured","",
             "The ranking caches record actual shared-host CPU batch runtimes, query and document counts, configured threads, load average and platform. Cached accesses reuse the original runtime receipt. These are offline batch measurements, with model warm-up and indexing effects described by the run records; they are not a hosted service latency, throughput or dollar-cost claim. No answer extractor was evaluated: retrieval metrics never prove answer correctness. The finite query-level sample does not establish production reliability.","",
             "With roughly four hundred questions, the worst-case 95% margin for a single independent Bernoulli proportion is about five percentage points. The paired design can be more sensitive when systems make correlated errors. Exact detectable effects depend on discordance; a universal power guarantee is not claimed.","",
             "Machine-readable per-query metrics, relevance ids, slice summaries, paired intervals and automatic error categories are in `results/heldout/`. The automated categories distinguish candidate misses from ranking/coverage failures; they are not a manual causal diagnosis.",""]
    (ROOT/"REPORT.md").write_text("\n".join(rows))
    svg='<svg xmlns="http://www.w3.org/2000/svg" width="660" height="285" viewBox="0 0 660 285"><rect width="660" height="285" fill="white"/><text x="5" y="15" font-size="13">Held-out nDCG@10: observed point estimates; intervals in REPORT.md</text>'+"".join(bars)+'</svg>'
    (ROOT/"results/heldout/ndcg.svg").write_text(svg)
    # Stable per-lesson evidence paths; do not duplicate giant per-query ranking files.
    dump(ROOT/"results/ax09/summary.json",dict(source="../heldout/results.json",decision=data["decision"],n_total=data["n_total"]))
    dump(ROOT/"results/ax02/summary.json",dict(source="../heldout/tool-policy.json",scope="deterministic tool-routing policy over known registry"))
    print("REPORT.md and stable ax02/ax09 evidence written")


if __name__=="__main__":
    main()
