"""Pinned input retrieval. Never silently accept a changed download."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / ".build"
DIST = ROOT / "dist"
LOCK = json.loads((ROOT / "sources.lock.json").read_text(encoding="utf-8"))


def run(*args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, **kwargs)


def sha256(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def download(name):
    spec = LOCK["downloads"][name]
    if not spec["sha256"]:
        raise RuntimeError(f"Unpinned checksum: {name}")
    dest = BUILD / "downloads" / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        tmp = dest.with_suffix(dest.suffix + ".part")
        run("curl.exe" if os.name == "nt" else "curl", "-fsSL", "--retry", "3", "--connect-timeout", "30", "-o", tmp, spec["url"])
        tmp.replace(dest)
    if sha256(dest) != spec["sha256"]:
        raise RuntimeError(f"SHA-256 mismatch: {dest}; remove cached file and retry")
    return dest


def source(name):
    spec = LOCK["sources"][name]
    dest = ROOT / "upstream" / name
    if not (dest / ".git").exists():
        dest.mkdir(parents=True, exist_ok=True)
        run("git", "init", dest)
        run("git", "-C", dest, "remote", "add", "origin", f"https://github.com/{spec['repo']}.git")
    head = subprocess.run(["git", "-C", str(dest), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if head != spec["commit"]:
        run("git", "-C", dest, "fetch", "--depth", "1", "origin", spec["commit"])
        run("git", "-C", dest, "checkout", "--detach", spec["commit"])
    return dest


def copy_contents(src, dest):
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest, dirs_exist_ok=True)
