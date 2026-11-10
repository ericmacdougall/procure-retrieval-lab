"""Fail closed on corpus drift; never silently update an already frozen experiment."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import ROOT,sha256_file,read_jsonl


def main():
    root=Path(ROOT)
    snapshot=json.loads((root/"data/ocds/SNAPSHOT.json").read_text())
    actual=sha256_file(str(root/"data/ocds/documents.jsonl"))
    if actual!=snapshot["documents_sha256"]:
        raise RuntimeError("Normalized corpus drift: recover the recorded snapshot; do not silently re-normalize")
    manifest=root/"data/ocds/manifest.jsonl"
    if sha256_file(str(manifest))!=snapshot["raw_manifest_sha256"]:
        raise RuntimeError("Raw manifest hash mismatch")
    for row in read_jsonl(str(manifest)):
        path=root/"data/ocds/raw"/row["file"]
        if sha256_file(str(path))!=row["sha256"]:
            raise RuntimeError("Raw snapshot hash mismatch: "+row["file"])
    if snapshot["documents"]<30000:
        raise RuntimeError("Corpus below declared volume")
    print("VERIFIED CORPUS",snapshot["documents"],"documents",snapshot["raw_files"],"raw files",actual)


if __name__=="__main__":
    main()
