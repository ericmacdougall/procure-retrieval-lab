# Pre-registration amendment history

## Version 1: retained, no sealed evaluation

`PREREG-v1-before-labelrepair.md` was recorded with SHA-256 `b7e85c763c57588580669a6d433b98f76ee07a1dca47fd353f066ba6beab3f1a` before the initial development run. The run completed three baseline arms and was stopped during reranking. Its log and `results/dev-v1-before-labelrepair/` are retained. No final configuration was selected and the actual held-out engine had zero opens.

## Version 2: general label repair before sealed evaluation

An independent blinded-to-system-scores label audit found four residual ambiguities after fixing a proposed-answer type bug. The repair decision follows those label/source findings, not retrieval performance:

- All semantic requirement queries receive buyer and award-date identity constraints, then receive a fresh blinded paraphrase preserving those constraints.
- Generic-title references and canonical supplier-name collisions receive an award-date qualifier when that does not reveal the requested answer.
- Record versions count as alternatives only when normalized buyer, supplier, title, value, currency and complete contract period agree. Missing periods never establish equivalence.
- Retrieval ranks and gold are collapsed by the query's required fact groups. A valid alias satisfies its group, redundant aliases receive no extra credit, and multi-hop questions still require separate groups.
- A no-answer item is rejected if an equivalent record remains available in the corpus; this rule applies to every split before evaluation.

The original repeated-prefix exclusions remain recorded. Previously rejected wording can return only after a changed blinded prompt passes the same validation. This changes the benchmark to clarified known-registry retrieval and makes it easier than natural ambiguous user queries. Source families can still cross splits, and query-level intervals may be optimistic.

Version 2 receives a new `PREREG.md` and source/question/config/runtime hashes before a new development search and before the sealed evaluation. Version 1 is not relabelled as a successful completed run.

## Final legal-alias refinement, still before the sealed evaluation

The clarified-query audit flagged one additional duplicate version: exact matching economic facts and contract period, with a trailing subscription-renewal title suffix and an Inc legal suffix. The same global source-normalization rule now strips only trailing lifecycle/legal suffixes; it retains the strict value, currency, supplier, buyer and complete period agreement. A negative control changes the value and proves the records do not collapse.

The intermediate pre-registration with SHA-256 `729c7f7c4669caf85c5ef3a22aa57d8cf5e4c028a543ae707f77d4ffe0f957eb` is retained as `PREREG-v2-before-legalalias-refinement.md`; no development search ran under it. The final pre-registration is `1ce801c4b7e0d10b495bf9f6ac2f1eaaaca4b8b9e16bffa87d280e648e297362`. Final blinded validation retains 2,138 queries (train 687, development 695, test-lock 342, held-out 414 including 354 answerable and 60 no-answer). Final independent audit: zero flagged among 154 stratified non-held-out cases; Wilson 95% upper bound approximately 2.4%, not proof of universally correct labels.
