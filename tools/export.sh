#!/usr/bin/env bash
# Write a clean, code-only export (no data, models, venv, caches, held-out) and print sizes.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="${1:-../ax11-lab-export}"
rm -rf "$OUT"
mkdir -p "$OUT"
tar --exclude=.venv --exclude=cache --exclude=data --exclude=heldout --exclude=logs --exclude=__pycache__ \
    --exclude=.pytest_cache --exclude='*.npy' --exclude=results/per_query --exclude='questions/FREEZE' -cf - . | tar -xf - -C "$OUT"
echo "export tree: $OUT"
du -sh "$OUT"
du -sh "$OUT"/* | sort -h | tail -12
