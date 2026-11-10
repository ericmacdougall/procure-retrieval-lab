"""Post-opening source-distribution exporter; original frozen engine remains unchanged."""
from pathlib import Path
import hashlib
import json
import sys
from public_replay import safe_file

DIRS=["src","tests","configs","tools"]

def export(root,target):
    root=Path(root).resolve();target=Path(target).resolve()
    if target.exists():raise ValueError("Export destination already exists; retained unchanged")
    if target.is_relative_to(root):raise ValueError("Export destination must be outside the source tree")
    inventory_path=safe_file(root,"PUBLIC_SOURCE_FILES.json")
    inventory_bytes=inventory_path.read_bytes()
    inventory=json.loads(inventory_bytes)
    if inventory.get("version")!=1 or not inventory.get("files") or "PUBLIC_SOURCE_FILES.json" in inventory["files"]:
        raise ValueError("Invalid checked-in source inventory")
    snapshots={"PUBLIC_SOURCE_FILES.json":inventory_bytes}
    for name,digest in inventory["files"].items():
        data=safe_file(root,name).read_bytes()
        if hashlib.sha256(data).hexdigest()!=digest:raise ValueError("Source inventory hash mismatch: "+name)
        snapshots[name]=data
    for directory in DIRS:
        folder=root/directory
        if folder.is_symlink() or not folder.is_dir() or not folder.resolve().is_relative_to(root):raise ValueError("Unsafe source directory")
        for path in folder.rglob("*"):
            if "__pycache__" in path.parts or path.suffix==".pyc":continue
            if path.is_symlink():raise ValueError("Source distribution refuses symlinks")
            if path.is_file() and str(path.relative_to(root)) not in inventory["files"]:raise ValueError("Unlisted source input refused")
    if sum(len(v) for v in snapshots.values())>50_000_000:raise ValueError("Source distribution exceeds fifty megabytes")
    target.mkdir(parents=True,mode=0o700)
    for name,data in snapshots.items():
        destination=target/name;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(data)
    print("EXPORTED_PUBLIC_SOURCE",target,"files",len(snapshots))

if __name__=="__main__":
    root=Path(__file__).resolve().parent
    export(root,Path(sys.argv[1]) if len(sys.argv)>1 else root.parent/"procure-retrieval-public-source")
