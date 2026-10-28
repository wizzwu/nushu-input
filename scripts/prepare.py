"""Build the same offline Rime resources for all three platforms."""
from pathlib import Path
import argparse
import json
import shutil
import zipfile
import importlib.metadata
from common import ROOT, BUILD, LOCK, run, source, download, sha256


def prepare():
    nushu = source("rime-nushu")
    source("unicode_nushu")
    font = source("noto-sans-nushu")
    squirrel_source = source("squirrel")
    engine = download("weasel.exe")
    extracted = BUILD / "weasel-extracted"
    if not (extracted / "data/luna_pinyin.schema.yaml").exists():
        sevenzip = shutil.which("7z") or shutil.which("7zz")
        if not sevenzip and (Path("C:/Program Files/7-Zip/7z.exe")).exists():
            sevenzip = "C:/Program Files/7-Zip/7z.exe"
        if not sevenzip:
            raise RuntimeError("Install 7-Zip (7z/7zz) before preparing resources")
        run(sevenzip, "x", engine, f"-o{extracted}", "-y", "-bso0")
    shared = BUILD / "shared"
    shared.mkdir(parents=True, exist_ok=True)
    data = extracted / "data"
    # Use the compatible schemas shipped by the pinned official Weasel release.
    # Newer Luna Pinyin changed simplifier option names and breaks the 2020 schema.
    for name in ["default.yaml", "key_bindings.yaml", "punctuation.yaml", "symbols.yaml",
                 "luna_pinyin.schema.yaml", "luna_pinyin_simp.schema.yaml", "luna_pinyin.dict.yaml",
                 "pinyin.yaml", "stroke.schema.yaml", "stroke.dict.yaml", "essay.txt"]:
        shutil.copy2(data / name, shared / name)
    shutil.copytree(data / "opencc", shared / "opencc", dirs_exist_ok=True)
    for p in nushu.glob("*.yaml"):
        shutil.copy2(p, shared / p.name)
    shutil.copytree(nushu / "opencc", shared / "opencc", dirs_exist_ok=True)
    fonts = BUILD / "fonts"
    fonts.mkdir(exist_ok=True)
    shutil.copy2(font / "NotoSansNushu-Regular.ttf", fonts / "NotoSansNushu-Regular.ttf")
    licenses = BUILD / "licenses"
    licenses.mkdir(exist_ok=True)
    for src, dest in [(nushu / "LICENSE", "rime-nushu.txt"), (font / "LICENSE", "NotoSansNushu-OFL.txt"),
                      (data.parent / "LICENSE.txt", "Weasel-LICENSE.txt"),
                      (squirrel_source / "LICENSE.txt", "Squirrel-LICENSE.txt")]:
        shutil.copy2(src, licenses / dest)
    for p in data.parent.glob("*license*.txt"):
        shutil.copy2(p, licenses / p.name)
    for component in ["PyYAML"]:
        distribution = importlib.metadata.distribution(component)
        for entry in distribution.files:
            if Path(str(entry)).name.upper() in ["LICENSE", "LICENSE.TXT"]:
                shutil.copy2(distribution.locate_file(entry), licenses / f"{component}-LICENSE.txt")
    provenance = {"sources": LOCK["sources"], "downloads": LOCK["downloads"],
                  "resources": {p.relative_to(BUILD).as_posix(): sha256(p)
                                for directory in [shared, fonts, licenses] for p in directory.rglob("*") if p.is_file()}}
    (BUILD / "resource-manifest.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Prepared {len(provenance['resources'])} pinned resource files")
    return shared


if __name__ == "__main__":
    prepare()
