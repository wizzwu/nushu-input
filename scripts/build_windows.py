from pathlib import Path
import os
import shutil
import zipfile
import yaml
from common import ROOT, BUILD, DIST, run, download, copy_contents
from prepare import prepare


def main():
    prepare()
    DIST.mkdir(exist_ok=True)
    license_text = (ROOT / "docs/安装许可.txt").read_text(encoding="utf-8") + "\n\n" + (ROOT / "LICENSE").read_text(encoding="utf-8")
    (BUILD / "windows-license.txt").write_text(license_text, encoding="utf-16")
    payload = BUILD / "windows-payload"
    payload.mkdir(exist_ok=True)
    for name in ["shared", "fonts", "licenses"]:
        copy_contents(BUILD / name, payload / name)
    shutil.copy2(download("weasel.exe"), payload / "weasel.exe")
    shutil.copy2(ROOT / "platforms/windows/install_user.py", payload / "install_user.py")
    shutil.copy2(ROOT / "docs/使用说明.txt", payload / "使用说明.txt")
    shutil.copy2(BUILD / "resource-manifest.json", payload / "resource-manifest.json")
    runtime = payload / "runtime"
    runtime.mkdir(exist_ok=True)
    with zipfile.ZipFile(download("python-embed.zip")) as archive:
        archive.extractall(runtime)
    # Pure-Python PyYAML avoids tying the installer to the build interpreter's ABI.
    for p in Path(yaml.__file__).parent.glob("*.py"):
        target = runtime / "yaml" / p.name
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(p, target)
    (runtime / "python312._pth").write_text("python312.zip\n.\n..\n", encoding="utf-8")
    nsis = BUILD / "tools/nsis-3.11/makensis.exe"
    if not nsis.exists():
        with zipfile.ZipFile(download("nsis.zip")) as archive:
            archive.extractall(BUILD / "tools")
    run(nsis, "/V2", "/INPUTCHARSET", "UTF8", ROOT / "platforms/windows/installer.nsi", cwd=ROOT)
    print(DIST / "NushuInput-Setup.exe")


if __name__ == "__main__":
    main()
