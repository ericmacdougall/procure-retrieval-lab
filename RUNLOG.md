# Recorded experiment and replay

The frozen engine is commit `5e3170c7673f74aa40d8f8ad14c3f60d7001ec1e`. All timestamps below are UTC on 10 November 2026. This is an offline experiment over public procurement records; it does not measure a deployed search service.

| Event | Evidence |
|---|---|
| 06:22:04 initial registration | Retained `PREREG-v1-before-labelrepair.md` and `logs/runlog.jsonl` |
| Initial development run interrupted after three arms | Independent label review found ambiguous source identity; original run records remain under `results/dev-v1-before-labelrepair` |
| Global label repair before final selection | Qualified all questions with buyer/contract identity; conservative equivalent-notice grouping prevents duplicate version credit; `PREREG-CHANGELOG.md` records amendments |
| 06:51:10 final registration | `PREREG.md` SHA-256 `1ce801c4b7e0d10b495bf9f6ac2f1eaaaca4b8b9e16bffa87d280e648e297362` |
| 06:56–07:06 final development search | Twenty-two preregistered configurations; frozen development-selected weighted fusion uses sparse weight 0.75 |
| 07:12:45 freeze | `questions/FREEZE` SHA-256 `eb5a45da72e8791547ee8a307bfc9f6a0b5c37daaac5057409574c5067e4b967` binds source, runtime, models, all questions, corpus, withheld identifiers, exact embeddings, config and registration |
| Sealed evaluation opened | All six arms ran on the same 414 questions, including 354 answerable and 60 constructed no-answer cases; `logs/heldout-access.log` records access |
| Actual evaluation, small benchmark and report | `logs/heldout-final.log`, `logs/small-benchmark-final.log` and corresponding result JSON; all processes exited zero |
| Stable replay | `timeout 900 bash run_lab.sh lab` exited zero: corpus hashes, 37 focused tests, recorded audit, frozen evaluation and report. Component/ranking caches were reused; this was not fresh independent model inference |

The model wording transformations and independent label judgments used bounded subscription inference through `gpt-6.1-sol`. Inputs contained public template text and required identity spans only. Maximum concurrency was two; finite attempts and schema validation rejected invalid outputs. The release contains data-only prompt/input/output artifacts, without autonomous agent transcripts or authentication material. The final stratified non-held-out label audit had zero flags in 154 cases, which does not prove that the dataset has no label errors.

The retained raw data contain original public supplier names. For the eleven protected-word occurrences in ten normalized records, independent anonymous government JSON requests returned HTTP 200 and the exact canonical release hashes matched the recovered snapshot, under OGL v3. `PUBLIC-DATA-PROVENANCE.json` records identifiers, public URLs, hashes and license. One development question copies its answer from one of those public records. The scope interpretation is an assumption distinguishing independently public data from private user or interview material; it does not change the frozen data.

The code history omits data, model weights, embeddings, private logs and credentials. The separately checksummed frozen experiment archive supplies the recorded corpus, questions, blinded data-only inference artifacts, caches, evaluation outputs and selected run logs. A replay proves consistency with these frozen artifacts. A cached replay cannot establish fresh model equivalence or production latency/capacity.
