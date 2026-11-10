import hashlib
import importlib.util
import json
from pathlib import Path
import pytest

PATH=Path(__file__).resolve().parents[1]/"public_replay.py"
spec=importlib.util.spec_from_file_location("public_replay",PATH)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

@pytest.fixture
def bundle(tmp_path):
    files=["src/a.py","requirements.lock.txt","PREREG.md","data/ocds/documents.jsonl","data/docs/withheld_ids.jsonl","heldout/questions.jsonl","questions/dev.jsonl","configs/final.json","cache/emb_a.npy","cache/rankings/a.json","data/ocds/manifest.jsonl"]
    for name in files:
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(name)
    snapshot=dict(raw_manifest_sha256=sha(tmp_path/"data/ocds/manifest.jsonl"))
    (tmp_path/"data/ocds/SNAPSHOT.json").write_text(json.dumps(snapshot))
    frozen={name:sha(tmp_path/name) for name in files if name not in ["cache/rankings/a.json","data/ocds/manifest.jsonl"]}
    receipt=dict(version=1,artifacts=frozen,runtime=dict(test="runtime"))
    (tmp_path/"questions/FREEZE").write_text(json.dumps(receipt))
    manifest=dict(version=1,raw_status="OMITTED/PUBLICPRIVACY",freeze_sha256=sha(tmp_path/"questions/FREEZE"),inputs={str(p.relative_to(tmp_path)):sha(p) for p in tmp_path.rglob("*") if p.is_file()})
    (tmp_path/"public-manifest.json").write_text(json.dumps(manifest))
    return tmp_path

def verify(root):return module.verify_inputs(root,runtime_reader=lambda:dict(test="runtime"))

def test_valid_unchanged_bundle(bundle):
    assert verify(bundle)["raw_status"]=="OMITTED/PUBLICPRIVACY"

@pytest.mark.parametrize("name",["cache/emb_a.npy","data/ocds/documents.jsonl","heldout/questions.jsonl","configs/final.json","cache/rankings/a.json","data/ocds/manifest.jsonl"])
@pytest.mark.parametrize("mutation",["missing","changed"])
def test_input_mutations_refuse_before_runtime(bundle,name,mutation):
    p=bundle/name
    p.unlink() if mutation=="missing" else p.write_text("changed")
    with pytest.raises(ValueError):module.verify_inputs(bundle,runtime_reader=lambda:pytest.fail("runtime/model import before input refusal"))

def test_runtime_change_refused(bundle):
    with pytest.raises(ValueError,match="runtime"):module.verify_inputs(bundle,runtime_reader=lambda:dict(test="changed"))

def test_unlisted_cache_refused(bundle):
    (bundle/"cache/unlisted.json").write_text("{}")
    with pytest.raises(ValueError):verify(bundle)

@pytest.mark.parametrize("name",["../escape","/absolute","cache/../escape","cache\\escape"])
def test_manifest_path_escape_refused(bundle,name):
    p=bundle/"public-manifest.json";d=json.loads(p.read_text());d["inputs"][name]="0"*64;p.write_text(json.dumps(d))
    with pytest.raises(ValueError):verify(bundle)

def test_symlink_refused(bundle,tmp_path):
    p=bundle/"cache/emb_a.npy";p.unlink();p.symlink_to(bundle/"requirements.lock.txt")
    with pytest.raises(ValueError):verify(bundle)

@pytest.mark.parametrize("left,right",[(["q1","q2"],["q1"]),(["q1","q1"],["q1","q2"]),(["q1","q2"],["q1","other"]),(["q2","q1"],["q1","q2"])])
def test_wrong_duplicate_incomplete_pair_ids_refuse(left,right):
    with pytest.raises(ValueError):module.validate_paired_ids(["q1","q2"],left,right)

def test_complete_pair_ids():
    module.validate_paired_ids(["q1","q2"],["q1","q2"],["q1","q2"])
