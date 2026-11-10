# Procurement retrieval lab: observed results

These are generated, paraphrased queries over real public UK procurement notices. The corpus is fixed and known to every retriever. Anchor-document splits are disjoint; equivalent notice versions, buyers and related contract families can recur across partitions. This establishes performance for this filtered benchmark, not production user-query quality or unseen-buyer generalization. Buyer/date qualifiers intentionally make the clarified registry task easier than raw user questions.

Metrics collapse legally normalized title/buyer/supplier/value/contract-period-equivalent source versions before ranking credit. One alias can satisfy its required fact group; redundant aliases earn no additional gain. Multi-hop questions retain separate required fact groups. This is required-fact-group retrieval, not a count of every duplicate source record.

The held-out set contains **414 questions**, of which **354 are answerable**. No-answer questions have a separate abstention evaluation and do not inflate the retrieval denominator.

Intervals below use ten thousand paired bootstrap resamples for differences, and ordinary query bootstrap intervals for individual means. These are conditional on this corpus and question-generation process; contract-family dependence may make query-level intervals optimistic. Slices are exploratory and not multiplicity-adjusted.

| System | nDCG@10 (95% CI) | Recall@10 (95% CI) | MRR@10 (95% CI) | Difference in nDCG vs BM25 |
|---|---|---|---|---|
| baseline-bm25 | 0.9797 [0.9691, 0.9888] | 0.9972 [0.9929, 1.0000] | 0.9801 [0.9669, 0.9915] | reference |
| baseline-dense | 0.9099 [0.8832, 0.9344] | 0.9435 [0.9195, 0.9647] | 0.9099 [0.8810, 0.9362] | -0.0698 [-0.0968, -0.0448] |
| baseline-hybrid | 0.9556 [0.9374, 0.9718] | 0.9845 [0.9703, 0.9958] | 0.9531 [0.9322, 0.9719] | -0.0241 [-0.0412, -0.0090] |
| baseline-rerank | 0.9366 [0.9176, 0.9536] | 0.9703 [0.9548, 0.9845] | 0.9440 [0.9229, 0.9632] | -0.0431 [-0.0613, -0.0261] |
| final-selected | 0.9860 [0.9762, 0.9938] | 0.9972 [0.9915, 1.0000] | 0.9860 [0.9746, 0.9953] | 0.0063 [0.0007, 0.0127] |
| tool-policy | 0.9563 [0.9348, 0.9749] | 0.9661 [0.9463, 0.9831] | 0.9526 [0.9301, 0.9725] | -0.0234 [-0.0457, -0.0038] |

## Pre-registered decision

Development selected `weight-0.75` from 22 declared configurations. The observed held-out decision is:

```json
{
  "deploy_better_retriever": true,
  "primary_difference": {
    "hi": 0.012715354367890152,
    "lo": 0.000680566461036766,
    "mean": 0.006315564098884697,
    "p_bootstrap": 0.03
  },
  "rule": "Publish evidence regardless of superiority; select no further configuration using these outcomes.",
  "slice_regressions_over_margin": [],
  "superiority_established": true
}
```

A nonpositive or uncertain result is reported without choosing another configuration on the held-out outcomes. The structured-tool policy is a separate deterministic routing arm; it is not a language-model planner.

## No-answer behavior

The threshold was calibrated on development questions, maximizing balanced answerability accuracy. The deliberately balanced slice mix is not a production prior; reported abstention precision will change with prevalence.

| System | Abstention precision | No-answer recall | Answerable coverage |
|---|---|---|---|
| baseline-bm25 | 0.5781 | 0.6167 | 0.9237 |
| baseline-dense | 0.3535 | 0.5833 | 0.8192 |
| baseline-hybrid | 0.4444 | 0.8000 | 0.8305 |
| baseline-rerank | 0.3304 | 0.6333 | 0.7825 |
| final-selected | 0.4434 | 0.7833 | 0.8333 |
| tool-policy | 0.7308 | 0.9500 | 0.9407 |

## Slice results

| System and slice | n | nDCG@10 with 95% CI |
|---|---|---|
| baseline-bm25: adversarial-neardup | 60 | 0.9938 [0.9815, 1.0000] |
| baseline-bm25: entity | 60 | 0.9917 [0.9750, 1.0000] |
| baseline-bm25: factoid-date | 60 | 0.9938 [0.9815, 1.0000] |
| baseline-bm25: factoid-numeric | 60 | 1.0000 [1.0000, 1.0000] |
| baseline-bm25: multi-hop | 60 | 0.9420 [0.9056, 0.9728] |
| baseline-bm25: paraphrase-heavy | 54 | 0.9543 [0.9065, 0.9907] |
| baseline-dense: adversarial-neardup | 60 | 0.7550 [0.6544, 0.8483] |
| baseline-dense: entity | 60 | 0.9877 [0.9692, 1.0000] |
| baseline-dense: factoid-date | 60 | 0.9833 [0.9500, 1.0000] |
| baseline-dense: factoid-numeric | 60 | 0.9683 [0.9331, 0.9938] |
| baseline-dense: multi-hop | 60 | 0.8656 [0.7991, 0.9226] |
| baseline-dense: paraphrase-heavy | 54 | 0.8981 [0.8220, 0.9615] |
| baseline-hybrid: adversarial-neardup | 60 | 0.8915 [0.8189, 0.9535] |
| baseline-hybrid: entity | 60 | 1.0000 [1.0000, 1.0000] |
| baseline-hybrid: factoid-date | 60 | 0.9898 [0.9693, 1.0000] |
| baseline-hybrid: factoid-numeric | 60 | 0.9905 [0.9715, 1.0000] |
| baseline-hybrid: multi-hop | 60 | 0.9224 [0.8759, 0.9611] |
| baseline-hybrid: paraphrase-heavy | 54 | 0.9376 [0.8778, 0.9881] |
| baseline-rerank: adversarial-neardup | 60 | 0.8999 [0.8397, 0.9532] |
| baseline-rerank: entity | 60 | 0.9815 [0.9569, 1.0000] |
| baseline-rerank: factoid-date | 60 | 0.9572 [0.9000, 1.0000] |
| baseline-rerank: factoid-numeric | 60 | 0.9760 [0.9459, 1.0000] |
| baseline-rerank: multi-hop | 60 | 0.8458 [0.7975, 0.8905] |
| baseline-rerank: paraphrase-heavy | 54 | 0.9615 [0.9113, 1.0000] |
| final-selected: adversarial-neardup | 60 | 1.0000 [1.0000, 1.0000] |
| final-selected: entity | 60 | 0.9938 [0.9815, 1.0000] |
| final-selected: factoid-date | 60 | 1.0000 [1.0000, 1.0000] |
| final-selected: factoid-numeric | 60 | 1.0000 [1.0000, 1.0000] |
| final-selected: multi-hop | 60 | 0.9598 [0.9305, 0.9837] |
| final-selected: paraphrase-heavy | 54 | 0.9599 [0.9074, 1.0000] |
| tool-policy: adversarial-neardup | 60 | 0.9500 [0.8833, 1.0000] |
| tool-policy: entity | 60 | 0.9938 [0.9815, 1.0000] |
| tool-policy: factoid-date | 60 | 1.0000 [1.0000, 1.0000] |
| tool-policy: factoid-numeric | 60 | 0.9667 [0.9167, 1.0000] |
| tool-policy: multi-hop | 60 | 0.9711 [0.9282, 1.0000] |
| tool-policy: paraphrase-heavy | 54 | 0.8450 [0.7482, 0.9283] |

## The twelve-question selection trap

A separate demonstration selected `bm25-k0.6-b0.75` by maximizing nDCG on 12 test-lock questions. Its selected-on score was 1.0000; on the remaining 280 answerable test-lock questions it was 0.9851. The observed difference was 0.0149. This contrast includes sample composition and sampling variation; it does not by itself identify a causal amount of selection bias.

The interval on the maximized twelve-question score is post-selection and not a valid confidence interval for the chosen model's generalization. The fresh set is disjoint; a difference also includes sampling variation.

## Label quality and task scope

Ambiguous repeated-prefix questions removed and buyer/date qualifiers added globally before the final development search, making the task easier than raw user queries. Legal-name/title/period/value-equivalent record versions count as one required fact group; multi-hop groups remain distinct. Known-source generated-query registry retrieval only.

32 ambiguous-prefix questions were removed before tuning. Full exclusions and split counts are in `questions/frozen-manifest.json`. The remaining labels still require the independent sample audit in `results/audit.json`.

## What is and is not measured

The ranking caches record actual shared-host CPU batch runtimes, query and document counts, configured threads, load average and platform. Cached accesses reuse the original runtime receipt. These are offline batch measurements, with model warm-up and indexing effects described by the run records; they are not a hosted service latency, throughput or dollar-cost claim. No answer extractor was evaluated: retrieval metrics never prove answer correctness. The finite query-level sample does not establish production reliability.

With roughly four hundred questions, the worst-case 95% margin for a single independent Bernoulli proportion is about five percentage points. The paired design can be more sensitive when systems make correlated errors. Exact detectable effects depend on discordance; a universal power guarantee is not claimed.

Machine-readable per-query metrics, relevance ids, slice summaries, paired intervals and automatic error categories are in `results/heldout/`. The automated categories distinguish candidate misses from ranking/coverage failures; they are not a manual causal diagnosis.


<!-- post-opening-editorial-correction -->
# Post-opening editorial correction

The frozen report generator labels all 32 excluded questions as ambiguous prefixes. The exact frozen question manifest and preregistration instead record **29 ambiguous-prefix exclusions and 3 semantic-rewording validation failures**. These are 32 total exclusions before the final tuning/freeze. No question, split, model selection, prediction, ranking, metric or confidence interval changes with this correction.

The original frozen generator and recorded artifacts are retained unchanged. The publication adapter appends this dated editorial correction to its regenerated report. This is a reporting repair after opening, not a new analysis or a held-out label repair. Recorded on 10 November 2026.
