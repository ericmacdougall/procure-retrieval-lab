"""Assemble unchanged computational inputs, with raw provenance packages withheld."""
from pathlib import Path
import hashlib
import json
import tarfile

ROOT=Path.home()/"lessons-authoring/ax11-lab"
WORK=Path.home()/".agent-harness/work/course-takeover-01a1c3fd/retrieval-release/public"
WORK.mkdir(parents=True,exist_ok=True,mode=0o700)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
paths=[]
for directory in ["data/ocds","data/docs","questions","heldout","llm-io","cache","results"]:
    paths.extend(p for p in (ROOT/directory).rglob("*") if p.is_file() and not p.is_symlink() and "__pycache__" not in p.parts and "raw" not in p.relative_to(ROOT).parts)
for name in ["runlog.jsonl","heldout-access.log","tune-final-20261110.log","small-benchmark-final.log","heldout-final.log","final-reproducible-rerun.log"]:
    paths.append(ROOT/"logs"/name)
paths.append(ROOT/"configs/final.json")
paths=sorted(set(paths))
inventory={str(p.relative_to(ROOT)):sha(p) for p in paths}
inventory_path=WORK/"artifact-manifest.json"
inventory_path.write_text(json.dumps(inventory,sort_keys=True,indent=2)+"\n")
manifest=dict(version=1,raw_status="OMITTED/PUBLICPRIVACY",freeze_sha256=sha(ROOT/"questions/FREEZE"),inventory_sha256=sha(inventory_path),inputs={k:v for k,v in inventory.items() if not k.startswith(("logs/","results/"))})
(WORK/"public-manifest.json").write_text(json.dumps(manifest,sort_keys=True,indent=2)+"\n")
target=WORK/"computational-inputs-v1.tar.gz"
assert not target.exists(),"Never overwrite an earlier artifact"
with tarfile.open(target,"w:gz",compresslevel=3) as archive:
    for path in paths:archive.add(path,arcname=str(path.relative_to(ROOT)),recursive=False)
    for name in ["artifact-manifest.json","public-manifest.json"]:archive.add(WORK/name,arcname=name)
receipt=dict(file=target.name,bytes=target.stat().st_size,sha256=sha(target),files=len(paths)+2,public_manifest_sha256=sha(WORK/"public-manifest.json"),source_ref="5e3170c7673f74aa40d8f8ad14c3f60d7001ec1e",raw_status="OMITTED/PUBLICPRIVACY",scope="Complete frozen computational inputs and recorded results; original raw344 provenance packages withheld, original manifest retained; no model weights, agent transcripts, credentials or virtualenv")
(WORK/"PUBLIC_ARTIFACT.json").write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps(receipt))
