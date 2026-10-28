"""Package reviewable source and reports; never include secrets or signing keys."""
from pathlib import Path
import argparse
import json
import shutil
import tarfile
import zipfile
from common import ROOT, BUILD, DIST, LOCK, sha256, source, run


def add_tree(archive, root, prefix, excluded=()):
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in excluded for part in relative.parts):
            continue
        if not path.is_file() or path.suffix in [".jks", ".keystore", ".pyc"] or path.name in ["keystore.properties", "local.properties"]:
            continue
        archive.add(path, arcname=str(Path(prefix) / relative), recursive=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--full-native-source", action="store_true")
    parser.add_argument("--native-source-only", action="store_true")
    parser.add_argument("--platform", choices=["windows", "macos", "android", "all"], default="all")
    args = parser.parse_args()
    DIST.mkdir(exist_ok=True)
    if args.full_native_source or args.native_source_only:
        src = source("trime")
        run("git", "-C", src, "submodule", "update", "--init", "--recursive", "--depth", "1")
        with tarfile.open(DIST / "Trime-3.3.4-native-source.tar.gz", "w:gz") as archive:
            add_tree(archive, src, "trime-3.3.4", excluded=(".git", ".gradle", "build", ".cxx"))
        if args.native_source_only:
            return
    with tarfile.open(DIST / "NushuInput-source.tar.gz", "w:gz") as archive:
        for directory in ["scripts", "platforms", "tests", "docs", ".github", "reports"]:
            add_tree(archive, ROOT / directory, directory, excluded=("__pycache__",))
        for name in ["README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "requirements.txt", "sources.lock.json", ".gitignore", ".gitattributes"]:
            archive.add(ROOT / name, arcname=name)
        android = BUILD / "android"
        if android.exists():
            add_tree(archive, android, "android-modified-source", excluded=(".gradle", "build", ".cxx", "prebuilt"))
    for name in ["resource-manifest.json"]:
        if (BUILD / name).exists():
            shutil.copy2(BUILD / name, DIST / name)
    for directory in ["licenses"]:
        if (BUILD / directory).exists():
            shutil.copytree(BUILD / directory, DIST / directory, dirs_exist_ok=True)
    shutil.copytree(ROOT / "reports", DIST / "reports", dirs_exist_ok=True)
    for path in (ROOT / "docs").iterdir():
        if path.is_file():
            shutil.copy2(path, DIST / path.name)
    shutil.copy2(ROOT / "THIRD_PARTY_NOTICES.md", DIST / "THIRD_PARTY_NOTICES.md")
    hashes = [f"{sha256(p)}  {p.relative_to(DIST).as_posix()}" for p in sorted(DIST.rglob("*")) if p.is_file() and p.name not in ["SHA256SUMS.txt", "NushuInput-delivery.zip"]]
    (DIST / "SHA256SUMS.txt").write_text("\n".join(hashes) + "\n", encoding="utf-8")
    with zipfile.ZipFile(DIST / "NushuInput-delivery.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(DIST.rglob("*")):
            if path.is_file() and path.name != "NushuInput-delivery.zip":
                archive.write(path, path.relative_to(DIST))
    print(f"Delivery: {DIST / 'NushuInput-delivery.zip'}")


if __name__ == "__main__":
    main()
