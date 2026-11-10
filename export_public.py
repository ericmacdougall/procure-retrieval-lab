"""Post-opening source-distribution exporter; original frozen engine remains unchanged."""
from pathlib import Path
import shutil
import sys

FILES=[".gitignore","README.md","LICENSE","LICENSES.md","Makefile","run_lab.sh","requirements.txt","requirements.lock.txt","PREREG.md","PREREG-CHANGELOG.md","PREREG-v1-before-labelrepair.md","PREREG-v2-before-legalalias-refinement.md","public_replay.py","export_public.py","PUBLIC_ARTIFACT.json","public-manifest.json","PUBLIC-DATA-PROVENANCE.json","REPORT.md","RUNLOG.md","LESSONS.md","ERRATA.md"]
DIRS=["src","tests","configs","tools"]

def export(root,target):
    root=Path(root).resolve();target=Path(target).resolve()
    if target.exists():raise ValueError("Export destination already exists; retained unchanged")
    paths=[root/name for name in FILES]
    for directory in DIRS:
        for path in (root/directory).rglob("*"):
            if "__pycache__" in path.parts or path.suffix==".pyc":continue
            if path.is_symlink():raise ValueError("Source distribution refuses symlinks")
            if path.is_file():paths.append(path)
    if any(p.is_symlink() or not p.is_file() for p in paths):raise ValueError("Missing or linked distribution input")
    if sum(p.stat().st_size for p in paths)>50_000_000:raise ValueError("Source distribution exceeds fifty megabytes")
    target.mkdir(parents=True,mode=0o700)
    for path in paths:
        destination=target/path.relative_to(root);destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,destination)
    print("EXPORTED_PUBLIC_SOURCE",target,"files",len(paths))

if __name__=="__main__":
    root=Path(__file__).resolve().parent
    export(root,Path(sys.argv[1]) if len(sys.argv)>1 else root.parent/"procure-retrieval-public-source")
