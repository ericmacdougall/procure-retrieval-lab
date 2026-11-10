import hashlib
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))


def test_empty_marker_cannot_unlock_holdout(tmp_path, monkeypatch):
    import guard
    marker = tmp_path / "FREEZE"
    marker.write_text("")
    questions = tmp_path / "questions.jsonl"
    questions.write_text('{"id":"never-show"}\n')
    monkeypatch.setattr(guard, "FREEZE", str(marker))
    monkeypatch.setattr(guard, "HELDOUT_FILE", str(questions))
    monkeypatch.setattr(guard, "HELDOUT_DIR", str(tmp_path))
    monkeypatch.setattr(guard, "LOG", str(tmp_path / "access.log"))
    with pytest.raises(guard.HeldoutLocked):
        guard.load_heldout("test-forged-marker")
    assert "OPENED" not in (tmp_path / "access.log").read_text()


def test_config_mutation_invalidates_frozen_experiment(tmp_path, monkeypatch):
    import guard
    root = tmp_path
    (root / "heldout").mkdir()
    (root / "heldout/questions.jsonl").write_text('{"id":"x"}\n')
    (root / "configs").mkdir()
    (root / "configs/final.json").write_text('{"selected":"bm25"}')
    (root / "PREREG.md").write_text("Metrics fixed in advance")
    (root / "src").mkdir()
    (root / "src/model.py").write_text("value = 1\n")
    (root / "data/docs").mkdir(parents=True)
    (root / "data/docs/withheld_ids.jsonl").write_text("")
    (root / "requirements.lock.txt").write_text("pinned")
    paths = ["heldout/questions.jsonl", "configs/final.json", "PREREG.md", "src/model.py","data/docs/withheld_ids.jsonl","requirements.lock.txt"]
    receipt = dict(version=1, artifacts={p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths},runtime=guard.runtime_settings())
    (root / "FREEZE").write_text(json.dumps(receipt))
    monkeypatch.setattr(guard, "ROOT", str(root))
    monkeypatch.setattr(guard, "FREEZE", str(root / "FREEZE"))
    monkeypatch.setattr(guard, "HELDOUT_FILE", str(root / "heldout/questions.jsonl"))
    monkeypatch.setattr(guard, "HELDOUT_DIR", str(root / "heldout"))
    monkeypatch.setattr(guard, "LOG", str(root / "access.log"))
    (root / "configs/final.json").write_text('{"selected":"changed-after-test"}')
    with pytest.raises(guard.HeldoutLocked, match="hash|integrity"):
        guard.load_heldout("tampered-config")


def test_valid_frozen_experiment_can_be_reproduced(tmp_path, monkeypatch):
    import guard
    root = tmp_path
    (root / "heldout").mkdir()
    (root / "heldout/questions.jsonl").write_text('{"id":"x"}\n')
    (root / "configs").mkdir()
    (root / "configs/final.json").write_text('{"selected":"bm25"}')
    (root / "PREREG.md").write_text("Fixed metrics")
    (root / "src").mkdir()
    (root / "src/model.py").write_text("value = 1\n")
    (root / "data/docs").mkdir(parents=True)
    (root / "data/docs/withheld_ids.jsonl").write_text("")
    (root / "requirements.lock.txt").write_text("pinned")
    paths = ["heldout/questions.jsonl", "configs/final.json", "PREREG.md", "src/model.py","data/docs/withheld_ids.jsonl","requirements.lock.txt"]
    receipt = dict(version=1, artifacts={p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths},runtime=guard.runtime_settings())
    (root / "FREEZE").write_text(json.dumps(receipt))
    for name, value in [("ROOT", str(root)), ("FREEZE", str(root / "FREEZE")),
                        ("HELDOUT_FILE", str(root / "heldout/questions.jsonl")),
                        ("HELDOUT_DIR", str(root / "heldout")), ("LOG", str(root / "access.log"))]:
        monkeypatch.setattr(guard, name, value)
    assert guard.load_heldout("first") == [{"id": "x"}]
    assert guard.load_heldout("reproduce-identical") == [{"id": "x"}]
    with monkeypatch.context() as context:
        context.setenv("AX11_THREADS","7")
        with pytest.raises(guard.HeldoutLocked,match="runtime"):
            guard.load_heldout("changed-runtime")
    (root/"data/docs/withheld_ids.jsonl").write_text('{"doc_id":"altered-corpus"}\n')
    with pytest.raises(guard.HeldoutLocked,match="hash"):
        guard.load_heldout("changed-withholding-mask")
