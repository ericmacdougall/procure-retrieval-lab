PY := .venv/bin/python
export AX11_THREADS ?= 6
export PYTHONHASHSEED := 0
export OMP_NUM_THREADS := $(AX11_THREADS)
export OPENBLAS_NUM_THREADS := $(AX11_THREADS)

.PHONY: setup bootstrap verify-data test quick tune freeze report lab export

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.lock.txt --extra-index-url https://download.pytorch.org/whl/cpu

bootstrap:
	$(PY) src/fetch.py 2024-03-04 26 2
	AX11_LAST_WINDOW=w2024-08-26 $(PY) src/normalise.py

verify-data:
	$(PY) src/verify_data.py

test:
	$(PY) -m pytest -q tests

quick: test
	$(PY) src/harness.py --system bm25 --split dev --quick

tune:
	$(PY) src/experiment.py tune
	$(PY) src/experiment.py small-benchmark

freeze:
	$(PY) src/experiment.py freeze

report:
	$(PY) src/report.py

lab: verify-data test
	$(PY) src/audit.py score
	@if [ ! -f questions/FREEZE ]; then $(MAKE) tune freeze; fi
	$(PY) src/heldout_eval.py
	$(MAKE) report

export:
	bash tools/export.sh
