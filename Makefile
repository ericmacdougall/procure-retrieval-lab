# procure-retrieval-lab (ax11 benchmark methodology, ax09 retrieval ladder, ax02 planner) -- phase 1 skeleton.
PY := .venv/bin/python
export AX11_THREADS ?= 16
export PYTHONHASHSEED := 0

.PHONY: setup fetch normalise questions paraphrase-batches paraphrase-merge baselines quick lab test export clean-cache

setup:
	python3 -m venv .venv && .venv/bin/pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

fetch:            ## resumable: weekly award-stage windows, 429-aware pacing
	$(PY) src/fetch.py 2024-03-04 52 2

normalise:
	$(PY) src/normalise.py

questions:        ## held-out drawn FIRST, then train/dev/testlock by doc-id hash. Reuses frozen files unless REGEN=1
	@if [ -f questions/dev.jsonl ] && [ -z "$(REGEN)" ]; then echo "questions frozen: reusing (REGEN=1 to rebuild)"; else $(PY) src/questions.py; fi

paraphrase-batches:
	$(PY) src/paraphrase.py batches

paraphrase-merge:
	$(PY) src/paraphrase.py merge

baselines:        ## defaults only, dev split, final question text
	for s in bm25 dense hybrid rerank; do $(PY) src/harness.py --system $$s --split dev; done

quick:            ## minutes: 150 dev questions, 2k-doc subset, all four baselines
	$(PY) -m pytest -q tests
	for s in bm25 dense hybrid rerank; do $(PY) src/harness.py --system $$s --split dev --quick; done

lab: fetch normalise questions   ## stages so far: fetch, normalise, questions, baselines (tune/freeze/heldout/report: builder 2)
	$(MAKE) baselines
	@echo "stages tune, freeze, heldout-eval, report: see HANDOFF-1.md (builder 2)"

test:
	$(PY) -m pytest -q tests

export:           ## code-only tree (no data, models, venv, caches) for publishing
	bash tools/export.sh

clean-cache:
	rm -rf cache
