"""Held-out guard.  The held-out question file can only be opened through load_heldout(), which
  1. refuses unless questions/FREEZE exists (written by the freeze stage, containing the final config hash),
  2. appends every attempt (allowed or refused) to logs/heldout-access.log.
Before the freeze the files are also chmod 000, so an accidental open fails at the OS level too.
Tuning code never imports this module's load_heldout (tests/test_guard.py greps for it)."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, QDIR, HELDOUT_DIR, read_jsonl

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
    log("OPENED", who)
    os.chmod(HELDOUT_DIR, 0o700)
    os.chmod(HELDOUT_FILE, 0o600)
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
