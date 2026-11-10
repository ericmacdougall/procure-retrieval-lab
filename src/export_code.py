"""Create a new code-only export directory without deleting an existing path."""
import pathlib
import shutil
import sys
from common import ROOT


def main():
    source=pathlib.Path(ROOT)
    target=pathlib.Path(sys.argv[1]).resolve() if len(sys.argv)>1 else source.parent/"procure-retrieval-export"
    if target.exists():
        raise RuntimeError("Export destination already exists; choose a new path")
    target.mkdir(parents=True)
    for name in ["src","tests","configs"]:
        shutil.copytree(source/name,target/name,ignore=shutil.ignore_patterns("__pycache__"))
    for name in ["README.md","LICENSE","LICENSES.md","Makefile","run_lab.sh","requirements.txt","requirements.lock.txt"]:
        shutil.copy2(source/name,target/name)
    total=sum(p.stat().st_size for p in target.rglob("*") if p.is_file())
    if total>50_000_000:
        raise RuntimeError("Code-only export exceeds 50MB; retained for inspection")
    print("EXPORTED",target,"bytes",total)


if __name__=="__main__":
    main()
