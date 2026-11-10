# Procurement retrieval lab

An offline, reproducible experiment over a fixed snapshot of real public procurement notices. It compares sparse retrieval, local sentence embeddings, reciprocal-rank and weighted fusion, a local cross-encoder reranker, and a deterministic tool-routing policy. The experiment includes real tuning runs, a pre-registration, sealed evaluation, query-level paired intervals, no-answer cases and a twelve-question selection-bias demonstration.

This is a known-corpus benchmark using generated and model-paraphrased queries. Gold-document splits are disjoint; buyers and related contract families can recur. It does not establish production accuracy, unseen-buyer generalization or answer correctness. There is no evaluated answer generator. Negative and inconclusive results are retained.

## Run

Run heavy stages on a Linux CPU host with sufficient RAM and disk. The recorded environment uses Python with the exact dependencies in `requirements.lock.txt`. The experiment defaults to six CPU threads because the host is shared.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock.txt --extra-index-url https://download.pytorch.org/whl/cpu
```

The release asset `computational-inputs-v1.tar.gz` supplies the unchanged normalized corpus, frozen questions, recorded data-only model judgments, embeddings, component/ranking caches, actual outputs and logs. Verify the asset SHA-256 against `PUBLIC_ARTIFACT.json`, then extract it into this checkout and run:

```sh
sha256sum computational-inputs-v1.tar.gz
# Compare with PUBLIC_ARTIFACT.json before extraction.
tar -xzf computational-inputs-v1.tar.gz
.venv/bin/python public_replay.py --audit-archive
```

`public_replay.py` is an explicitly post-opening publication adapter outside the original frozen engine. It checks every archived file before the first run, verifies all original computational freeze hashes and exact runtime, runs the focused tests and recorded audit, repeats the fixed twelve-question demonstration, and executes the unchanged held-out evaluation and report. It selects no new held-out configuration. Later identical replays can omit `--audit-archive` because result/log files have been regenerated; immutable inputs and caches are still verified on every run. These are cached computational replays, not fresh model inference. The exact runtime may require the recorded Python version in addition to the dependency lock.

**Raw provenance check: OMITTED/PUBLICPRIVACY.** The original 344 downloaded government packages are withheld from this public bundle while preserving their unchanged hash manifest and snapshot metadata. Complete computational inputs are present. The raw directory also contained 317 unrelated later-window files, which are not experimental inputs and are not exported. Raw downloads can include unsafe URLs or credential-shaped prose; public origin is not sufficient permission to redistribute credentials. The original private raw archive is retained. `PUBLIC-DATA-PROVENANCE.json` independently traces all matching protected-name occurrences in the normalized corpus to anonymously accessible OGL government releases with exact content hashes. No names, frozen questions or measured values were masked or changed for publication.

The original `bash run_lab.sh lab` (also `make lab`) remains unchanged and performs the full raw-package verification. It requires the original raw packages and was independently replayed successfully in an isolated private extraction. The public adapter does not claim to perform that raw verification. `make bootstrap` downloads the original March–August 2024 award windows, but current API responses can differ from the recorded snapshot; drift is rejected rather than silently replacing the experiment. Model weights are separate downloads under their original licenses.

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
- `public_replay.py`, `public-manifest.json`, `PUBLIC_ARTIFACT.json`: post-opening public replay and exact publication hashes.
- `PUBLIC-DATA-PROVENANCE.json`: anonymous public source verification for normalized supplier-name matches.
- `REPORT.md`, `RUNLOG.md`, `LESSONS.md`: walkthroughs derived from the run artifacts.

## Models and measurement

Dense retrieval uses `BAAI/bge-small-en-v1.5`, revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, with the published English query instruction and normalized cosine scores. The cross-encoder uses `cross-encoder/ms-marco-MiniLM-L6-v2`, revision `233902d25c440f23af6f7d6e94d2946bac0bee0a`. Both run on CPU. The recovered embedding cache was generated from the recorded corpus with the same sole locally cached BGE revision; its text hash is part of the cache identity. New source or query changes invalidate ranking caches.

Timing artifacts report the actual workload, thread setting, CPU availability and load average. Cached runs refer to their original measurement. These offline batch measurements do not establish service p95 latency, multi-tenant capacity, throughput under representative production load, or dollar costs.

See `LICENSES.md` for upstream terms. This project's code is MIT licensed. Public data and model weights retain their own licences.

`bash tools/export.sh DESTINATION` (or `make export`) creates a complete code-only distribution, including the original preregistration, post-opening adapters, publication manifests, docs and tests. It omits all experiment data and caches; install the separately checksummed computational-inputs asset to replay it. The frozen historical `src/export_code.py` remains unchanged and is superseded by root `export_public.py` for publication.

See `ERRATA.md` for the post-opening editorial correction: the 32 total exclusions comprise 29 ambiguous prefixes and 3 semantic-rewording validation failures. The frozen report generator's older aggregate label is retained with that correction appended by the publication adapter; results and statistical decisions are unchanged.
