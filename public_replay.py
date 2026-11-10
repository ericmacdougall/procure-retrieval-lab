"""Post-opening public replay. Original frozen engine and full raw verifier stay unchanged."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import platform
import subprocess
import sys

INPUT_DIRS=("data/docs","data/ocds","questions","heldout","llm-io","cache")
REQUIRED={"heldout/questions.jsonl","configs/final.json","PREREG.md","requirements.lock.txt","data/ocds/documents.jsonl","data/docs/withheld_ids.jsonl"}

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda:stream.read(1024*1024),b""):h.update(part)
    return h.hexdigest()

def safe_file(root,name):
    path=PurePosixPath(name)
    if not name or path.is_absolute() or "\\" in name or any(x in (".","..","") for x in name.split("/")):
        raise ValueError("Unsafe manifest path")
    current=root
    for component in path.parts:
        current=current/component
        if current.is_symlink():raise ValueError("Symlink in public artifact: "+name)
    if not current.is_file() or not current.resolve().is_relative_to(root.resolve()):
        raise ValueError("Missing/escaped input: "+name)
    return current

def actual_runtime():
    # Metadata lookup does not import or initialize a model.
    return dict(dense_revision="5c38ec7c405ec4b44b94cc5a9bb96e735b38267a",dense_model="BAAI/bge-small-en-v1.5",
        dense_maxlen=int(os.getenv("AX11_MAXLEN","192")),query_prefix="Represent this sentence for searching relevant passages: ",
        reranker_revision="233902d25c440f23af6f7d6e94d2946bac0bee0a",reranker="cross-encoder/ms-marco-MiniLM-L6-v2",
        threads=int(os.getenv("AX11_THREADS","6")),python=platform.python_version(),
        packages={name:importlib.metadata.version(name) for name in ["numpy","scipy","torch","sentence-transformers","transformers"]})

def verify_inputs(root,runtime_reader=actual_runtime):
    root=Path(root)
    manifest=json.loads(safe_file(root,"public-manifest.json").read_text())
    if manifest.get("version")!=1 or manifest.get("raw_status")!="OMITTED/PUBLICPRIVACY" or not manifest.get("inputs"):
        raise ValueError("Incomplete public manifest")
    for name,digest in manifest["inputs"].items():
        if not isinstance(digest,str) or len(digest)!=64 or sha(safe_file(root,name))!=digest:
            raise ValueError("Public input hash mismatch: "+name)
        if name.startswith("data/raw/") or name.startswith("data/ocds/raw/"):
            raise ValueError("Raw packages are not part of the public replay")
    expected={p for p in manifest["inputs"] if any(p.startswith(d+"/") for d in INPUT_DIRS)}
    actual=set()
    for directory in INPUT_DIRS:
        for p in (root/directory).rglob("*"):
            if p.is_symlink():raise ValueError("Symlink in public input tree")
            if p.is_file():actual.add(str(p.relative_to(root)))
    if actual!=expected:raise ValueError("Public input inventory is incomplete or has unlisted files")
    freeze_path=safe_file(root,"questions/FREEZE")
    if sha(freeze_path)!=manifest.get("freeze_sha256"):raise ValueError("Original freeze receipt changed")
    receipt=json.loads(freeze_path.read_text())
    sources={str(p.relative_to(root)) for p in (root/"src").glob("*.py")}
    artifacts=receipt.get("artifacts",{})
    if receipt.get("version")!=1 or not sources or not (REQUIRED|sources).issubset(artifacts):
        raise ValueError("Incomplete original computational freeze")
    for name,digest in artifacts.items():
        if sha(safe_file(root,name))!=digest:raise ValueError("Original frozen input mismatch: "+name)
    snapshot=json.loads(safe_file(root,"data/ocds/SNAPSHOT.json").read_text())
    if sha(safe_file(root,"data/ocds/manifest.jsonl"))!=snapshot["raw_manifest_sha256"]:
        raise ValueError("Original raw provenance manifest changed")
    if receipt.get("runtime")!=runtime_reader():raise ValueError("Frozen runtime settings changed")
    return manifest

def validate_paired_ids(expected,left,right):
    if len(expected)!=len(set(expected)) or any(len(x)!=len(expected) or len(x)!=len(set(x)) or list(x)!=list(expected) for x in [left,right]):
        raise ValueError("Wrong, duplicate, incomplete or reordered paired question IDs")

def audit_archive(root,manifest):
    path=safe_file(root,"artifact-manifest.json")
    if sha(path)!=manifest["inventory_sha256"]:raise ValueError("Archive inventory changed")
    inventory=json.loads(path.read_text())
    for name,digest in inventory.items():
        if sha(safe_file(root,name))!=digest:raise ValueError("Archived file mismatch: "+name)
    if not set(manifest["inputs"]).issubset(inventory):raise ValueError("Inputs absent from archive inventory")
    # Source files come from the separately versioned code checkout, not the data archive.
    allowed=set(inventory)|{"artifact-manifest.json","public-manifest.json"}
    for directory in INPUT_DIRS:
        for p in (root/directory).rglob("*"):
            if p.is_file() and str(p.relative_to(root)) not in allowed:raise ValueError("Unlisted archive input")

def run(root,audit=False):
    os.environ.setdefault("AX11_THREADS","6")
    os.environ.setdefault("OMP_NUM_THREADS",os.environ["AX11_THREADS"])
    os.environ.setdefault("OPENBLAS_NUM_THREADS",os.environ["AX11_THREADS"])
    manifest=verify_inputs(root)
    if audit:audit_archive(root,manifest)
    print("RAW_PROVENANCE_CHECK OMITTED/PUBLICPRIVACY; normalized corpus and all original computational freeze hashes verified",flush=True)
    # Original guard independently verifies source/runtime/input hashes before opening.
    sys.path.insert(0,str(root/"src"))
    import guard
    qs=guard.load_heldout("public_replay.post_opening")
    expected=[q["id"] for q in qs]
    for command in [[sys.executable,"-m","pytest","-q","tests"],[sys.executable,"src/audit.py","score"],[sys.executable,"src/experiment.py","small-benchmark"],[sys.executable,"src/heldout_eval.py"],[sys.executable,"src/report.py"]]:
        subprocess.run(command,cwd=root,check=True)
    result=json.loads((root/"results/heldout/results.json").read_text())
    systems=result["systems"]
    base=systems["baseline-bm25"]["qids"]
    for arm in systems.values():
        validate_paired_ids(expected,base,arm["qids"])
        if len(arm["rankings"])!=len(expected) or len(arm["top_scores"])!=len(expected):
            raise ValueError("Output ranking cardinality mismatch")
    print("PUBLIC_REPLAY_COMPLETE: original frozen evaluation/report regenerated; cached computational replay, no new selection",flush=True)

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-archive",action="store_true",help="Verify every archived output too; use before first replay in a fresh extraction")
    args=parser.parse_args()
    run(Path(__file__).resolve().parent,audit=args.audit_archive)
