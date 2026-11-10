#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export AX11_THREADS="${AX11_THREADS:-6}"
export PYTHONHASHSEED=0
export OMP_NUM_THREADS="$AX11_THREADS"
export OPENBLAS_NUM_THREADS="$AX11_THREADS"
PY=.venv/bin/python
stage="${1:-lab}"
if [[ "$stage" == quick ]]; then
    "$PY" -m pytest -q tests
    "$PY" src/harness.py --system bm25 --split dev --quick
elif [[ "$stage" == lab ]]; then
    "$PY" src/verify_data.py
    "$PY" -m pytest -q tests
    "$PY" src/audit.py score
    if [[ ! -f questions/FREEZE ]]; then
        "$PY" src/experiment.py tune
        "$PY" src/experiment.py small-benchmark
        "$PY" src/experiment.py freeze
    fi
    "$PY" src/heldout_eval.py
    "$PY" src/report.py
else
    printf 'Usage: bash run_lab.sh [quick|lab]\n' >&2
    exit 2
fi
