# Procurement retrieval lab

An offline, reproducible experiment over a fixed snapshot of real public procurement notices. It compares sparse retrieval, local sentence embeddings, reciprocal-rank and weighted fusion, a local cross-encoder reranker, and a deterministic tool-routing policy. The experiment includes real tuning runs, a pre-registration, sealed evaluation, query-level paired intervals, no-answer cases and a twelve-question selection-bias demonstration.

This is a known-corpus benchmark using generated and model-paraphrased queries. Gold-document splits are disjoint; buyers and related contract families can recur. It does not establish production accuracy, unseen-buyer generalization or answer correctness. There is no evaluated answer generator. Negative and inconclusive results are retained.

## Run

Run heavy stages on a Linux CPU host with sufficient RAM and disk. The recorded environment uses Python with the exact dependencies in `requirements.lock.txt`. The experiment defaults to six CPU threads because the host is shared.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock.txt --extra-index-url https://download.pytorch.org/whl/cpu
.venv/bin/python src/verify_data.py
bash run_lab.sh quick
bash run_lab.sh lab
```

`bash run_lab.sh lab` (also available as `make lab`) starts from the recorded downloaded corpus, frozen blinded question files and independent audit inputs/outputs. It verifies the corpus, runs the focused checks and audit, performs the declared development-only search, records a final configuration and hash receipt, opens the sealed evaluation, and writes `REPORT.md`. After the freeze, rerunning evaluates only the identical hashed experiment; it cannot retune a different model against the same evaluation cases.

`make bootstrap` fetches the March through August 2024 Contracts Finder award windows. An API can change after a snapshot; `make verify-data` rejects drift instead of silently replacing the experiment. The snapshot manifest, frozen questions and model-inference audit trail are experimental artifacts, separate from large model weights and embedding caches. A code-only checkout does not manufacture missing model judgments or substitute generated labels for an independent audit. Publication of those artifacts is tracked as an explicit delivery gate.

Question wording was transformed through a subscription model in blinded batches containing only template text and required identity spans, with finite execution receipts. No provider API key is used. Original templates, validated paraphrases, rejected transformations, exact model identifiers and prompt hashes form the audit trail. The held-out text is sealed before tuning. This is an accidental-leakage discipline, not a security boundary against a malicious owner with filesystem access.

## Layout

- `src/`: normalization, question generation, validation, retrieval, tool policy, metrics, tuning, frozen evaluation and reporting.
- `tests/`: metric controls, missing-reference abstention, duplicate-title identity selection, paraphrase validation and frozen-artifact mutation controls.
- `configs/final.json`: the development-selected configuration and answerability thresholds.
- `PREREG.md`: declared selection budget, metrics, sample sizes, thresholds and known limitations recorded before tuning.
- `questions/FREEZE`: exact hashes of source, corpus, questions, configuration and pre-registration.
- `results/heldout/`: observed metrics, paired intervals, slice/error analysis and figure.
- `results/ax11/`: twelve-question maximization contrast.
- `results/ax09/` and `results/ax02/`: stable per-topic result references.
- `logs/runlog.jsonl`: timestamped development decisions and measured runtimes.
- `REPORT.md`, `RUNLOG.md`, `LESSONS.md`: walkthroughs derived from the run artifacts.

## Models and measurement

Dense retrieval uses `BAAI/bge-small-en-v1.5`, revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, with the published English query instruction and normalized cosine scores. The cross-encoder uses `cross-encoder/ms-marco-MiniLM-L6-v2`, revision `233902d25c440f23af6f7d6e94d2946bac0bee0a`. Both run on CPU. The recovered embedding cache was generated from the recorded corpus with the same sole locally cached BGE revision; its text hash is part of the cache identity. New source or query changes invalidate ranking caches.

Timing artifacts report the actual workload, thread setting, CPU availability and load average. Cached runs refer to their original measurement. These offline batch measurements do not establish service p95 latency, multi-tenant capacity, throughput under representative production load, or dollar costs.

See `LICENSES.md` for upstream terms. This project's code is MIT licensed. Public data and model weights retain their own licences.
