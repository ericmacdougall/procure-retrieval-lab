"""Held-out guard.  The held-out question file can only be opened through load_heldout(), which
  1. refuses unless questions/FREEZE exists (written by the freeze stage, containing the final config hash),
  2. appends every attempt (allowed or refused) to logs/heldout-access.log.
Before the freeze the files are also chmod 000, so an accidental open fails at the OS level too.
Tuning code never imports this module's load_heldout (tests/test_guard.py greps for it)."""
import os
import sys
import time
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, QDIR, HELDOUT_DIR, read_jsonl, sha256_file

FREEZE = os.path.join(QDIR, "FREEZE")
LOG = os.path.join(ROOT, "logs", "heldout-access.log")
HELDOUT_FILE = os.path.join(HELDOUT_DIR, "questions.jsonl")


class HeldoutLocked(Exception):
    pass


def log(event, who):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write("%s pid=%d %s caller=%s argv=%s" % (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), os.getpid(), event, who, " ".join(sys.argv)) + chr(10))


def load_heldout(who="unknown"):
    if not os.path.exists(FREEZE):
        log("REFUSED(no FREEZE)", who)
        raise HeldoutLocked("held-out is locked until questions/FREEZE exists")
    try:
        with open(FREEZE) as f:
            receipt = json.load(f)
        artifacts = receipt["artifacts"]
        required = {"heldout/questions.jsonl", "configs/final.json", "PREREG.md","data/docs/withheld_ids.jsonl","requirements.lock.txt"}
        sources = {str(p.relative_to(ROOT)) for p in Path(ROOT).joinpath("src").glob("*.py")}
        if receipt.get("version") != 1 or not sources or not (required | sources).issubset(artifacts):
            raise ValueError("incomplete hash receipt")
        if receipt.get("runtime")!=runtime_settings():
            raise ValueError("runtime settings changed after freeze")
        os.chmod(HELDOUT_DIR, 0o700)
        os.chmod(HELDOUT_FILE, 0o600)
        for relative, expected in artifacts.items():
            path = Path(ROOT).joinpath(relative).resolve()
            if not path.is_relative_to(Path(ROOT).resolve()) or sha256_file(str(path)) != expected:
                raise ValueError("hash mismatch: " + relative)
    except (ValueError, KeyError, OSError, TypeError) as error:
        log("REFUSED(integrity)", who)
        raise HeldoutLocked("frozen experiment integrity/hash check failed: " + str(error)) from error
    log("OPENED verified_hash_receipt", who)
    return read_jsonl(HELDOUT_FILE)


def build_write(path, rows, who="build"):
    """Pre-freeze writer used by the question builder only (logged)."""
    from common import write_jsonl
    log("WRITE " + os.path.basename(path), who)
    os.makedirs(HELDOUT_DIR, exist_ok=True)
    os.chmod(HELDOUT_DIR, 0o700)
    if os.path.exists(path):
        os.chmod(path, 0o600)
    write_jsonl(path, rows)


def seal():
    """chmod 000 the held-out directory (called when its hash is recorded in the pre-registration)."""
    for fn in os.listdir(HELDOUT_DIR):
        os.chmod(os.path.join(HELDOUT_DIR, fn), 0)
    os.chmod(HELDOUT_DIR, 0)
    log("SEALED", "build")


def freeze_experiment():
    """Metadata-only freeze stage; never parses sealed questions or chooses a model."""
    if os.path.exists(FREEZE):
        print("Already frozen; evaluator will verify all artifact hashes")
        return
    root=Path(ROOT)
    manifest=json.loads((root/"questions/frozen-manifest.json").read_text())
    os.chmod(HELDOUT_DIR,0o700)
    os.chmod(HELDOUT_FILE,0o600)
    if sha256_file(HELDOUT_FILE)!=manifest["heldout_sha256"]:
        seal()
        raise HeldoutLocked("heldout hash changed after question freeze")
    paths=[root/"configs/final.json",root/"PREREG.md",Path(HELDOUT_FILE)]
    paths+=list((root/"src").glob("*.py"))+list((root/"questions").glob("*.jsonl"))
    paths+=[root/"data/ocds/documents.jsonl",root/"data/docs/withheld_ids.jsonl",root/"requirements.lock.txt"]
    paths+=list((root/"cache").glob("emb_*.npy"))
    receipt=dict(version=1,timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
                 artifacts={str(p.relative_to(root)):sha256_file(str(p)) for p in paths},runtime=runtime_settings())
    Path(FREEZE).write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    seal()
    print("FROZEN",sha256_file(FREEZE),flush=True)


def runtime_settings():
    import dense,rerank,importlib.metadata,platform
    return dict(dense_revision=dense.REVISION,dense_model=dense.MODEL,dense_maxlen=dense.MAXLEN,
                query_prefix=dense.QPREFIX,reranker_revision=rerank.REVISION,reranker=rerank.RERANKER,
                threads=int(os.environ.get("AX11_THREADS","6")),python=platform.python_version(),
                packages={name:importlib.metadata.version(name) for name in ["numpy","scipy","torch","sentence-transformers","transformers"]})


def reopen_for_question_build():
    if os.path.exists(FREEZE):
        raise HeldoutLocked("Cannot rebuild questions after experiment freeze")
    os.chmod(HELDOUT_DIR,0o700)
    for path in Path(HELDOUT_DIR).glob("*"):
        os.chmod(path,0o600)
    log("REOPEN_BUILD_PRE_FREEZE","question-build")
