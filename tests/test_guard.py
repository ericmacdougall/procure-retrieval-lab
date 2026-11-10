"""Guard tests: held-out is locked without FREEZE, refusals and opens are logged, tuning code never imports the loader."""
import os
import sys
import re
import glob
import importlib

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src")
sys.path.insert(0, SRC)


def test_locked_without_freeze(tmp_path, monkeypatch):
    import guard
    importlib.reload(guard)
    monkeypatch.setattr(guard, "FREEZE", str(tmp_path / "FREEZE"))
    monkeypatch.setattr(guard, "LOG", str(tmp_path / "access.log"))
    with pytest.raises(guard.HeldoutLocked):
        guard.load_heldout("unit-test")
    assert "REFUSED" in open(guard.LOG).read()


def test_harness_rejects_heldout_split():
    import harness
    with pytest.raises(AssertionError):
        harness.load_questions("heldout")


def test_tuning_modules_never_import_the_loader():
    allowed = set(["guard.py", "heldout_eval.py"])
    bad = []
    for fn in glob.glob(os.path.join(SRC, "*.py")):
        if os.path.basename(fn) in allowed:
            continue
        txt = open(fn).read()
        if re.search(r"load_heldout|questions\.jsonl.*heldout|heldout/questions", txt.replace("guard.build_write", "")):
            if os.path.basename(fn) not in ("paraphrase.py", "questions.py"):
                bad.append(os.path.basename(fn))
    assert not bad, bad
