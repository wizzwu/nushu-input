"""Tiny offline editor used only on our temporary Android emulator."""
from pathlib import Path
import json
import os
import shutil
import zipfile
from common import ROOT, BUILD, run


def main():
    sdk = Path(os.environ.get("ANDROID_HOME") or Path(os.environ["LOCALAPPDATA"]) / "Android/Sdk")
    tools = sdk / "build-tools/35.0.0"
    java = Path(os.environ["JAVA_HOME"]) / "bin"
    jar = sdk / "platforms/android-35/android.jar"
    target = BUILD / "android-fixture"
    classes, dex = target / "classes", target / "dex"
    classes.mkdir(parents=True, exist_ok=True)
    dex.mkdir(exist_ok=True)
    run(java / "javac.exe", "-source", "8", "-target", "8", "-encoding", "UTF-8", "-bootclasspath", jar,
        "-d", classes, ROOT / "tests/android/MainActivity.java")
    run(java / "jar.exe", "cf", target / "fixture.jar", "-C", classes, ".")
    run(tools / "d8.bat", "--lib", jar, "--output", dex, target / "fixture.jar")
    unsigned = target / "fixture-unsigned.apk"
    run(tools / "aapt.exe", "package", "-f", "-M", ROOT / "tests/android/AndroidManifest.xml", "-I", jar, "-A", BUILD / "fonts", "-F", unsigned)
    with zipfile.ZipFile(unsigned, "a") as apk:
        apk.write(dex / "classes.dex", "classes.dex")
    aligned = target / "fixture-aligned.apk"
    run(tools / "zipalign.exe", "-f", "4", unsigned, aligned)
    config = json.loads((Path.home() / ".codex/secrets/nushu-input/signing.json").read_text())
    env = dict(os.environ, FIXTURE_STORE_PASSWORD=config["storePassword"], FIXTURE_KEY_PASSWORD=config["keyPassword"])
    run(tools / "apksigner.bat", "sign", "--ks", config["storeFile"], "--ks-key-alias", config["keyAlias"],
        "--ks-pass", "env:FIXTURE_STORE_PASSWORD", "--key-pass", "env:FIXTURE_KEY_PASSWORD", "--out", target / "fixture.apk", aligned, env=env)
    print(target / "fixture.apk")


if __name__ == "__main__":
    main()
