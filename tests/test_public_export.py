"""A source distribution must collect its tests before any large data is installed."""
from pathlib import Path
import os
import json
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]

def test_public_export_is_complete_and_collects_tests(tmp_path):
    target=tmp_path/"export"
    env=os.environ.copy();env["PYTHON"]=sys.executable
    subprocess.run(["bash",str(ROOT/"tools/export.sh"),str(target)],cwd=ROOT,env=env,check=True)
    for name in ["public_replay.py","export_public.py","PREREG.md","PREREG-CHANGELOG.md","PUBLIC_ARTIFACT.json","public-manifest.json","PUBLIC-DATA-PROVENANCE.json","REPORT.md","RUNLOG.md","LESSONS.md","ERRATA.md","requirements.lock.txt","tools/export.sh"]:
        assert (target/name).is_file(),name
    assert not any((target/name).exists() for name in [".git",".venv","cache","data","heldout","llm-io","logs","results"])
    result=subprocess.run([sys.executable,"-m","pytest","--collect-only","-q","tests"],cwd=target,env=env,capture_output=True,text=True,timeout=60)
    assert result.returncode==0,result.stdout+result.stderr
    assert "tests collected" in result.stdout

def test_export_refuses_existing_destination(tmp_path):
    target=tmp_path/"existing";target.mkdir();(target/"keep").write_text("preserve")
    env=os.environ.copy();env["PYTHON"]=sys.executable
    result=subprocess.run(["bash",str(ROOT/"tools/export.sh"),str(target)],cwd=ROOT,env=env,capture_output=True,text=True)
    assert result.returncode!=0
    assert (target/"keep").read_text()=="preserve"

def copy_source(target):
    inventory=json.loads((ROOT/"PUBLIC_SOURCE_FILES.json").read_text())
    for name in ["PUBLIC_SOURCE_FILES.json",*inventory["files"]]:
        dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,dest)
    return target

def attempt(root,target):
    return subprocess.run([sys.executable,str(root/"export_public.py"),str(target)],cwd=root,capture_output=True,text=True)

def test_directory_symlink_to_outside_canary_refused(tmp_path):
    root=copy_source(tmp_path/"source");outside=tmp_path/"outside";outside.mkdir();(outside/"canary.txt").write_text("synthetic canary")
    shutil.rmtree(root/"tools");(root/"tools").symlink_to(outside,target_is_directory=True)
    target=tmp_path/"export";result=attempt(root,target)
    assert result.returncode!=0 and not target.exists()

def test_untracked_environment_canary_refused(tmp_path):
    root=copy_source(tmp_path/"source");(root/"tools/.env").write_text("synthetic canary")
    target=tmp_path/"export";result=attempt(root,target)
    assert result.returncode!=0 and not target.exists()

def test_target_inside_source_refused(tmp_path):
    root=copy_source(tmp_path/"source");target=root/"src/nested-export";result=attempt(root,target)
    assert result.returncode!=0 and not target.exists()
