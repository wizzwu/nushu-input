"""Sign a cloud-built unsigned APK locally with the existing persistent key."""
from pathlib import Path
import argparse
import json
import os
import zipfile
from common import ROOT, BUILD, DIST, run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("apk", type=Path)
    args = parser.parse_args()
    config = json.loads((Path.home() / ".codex/secrets/nushu-input/signing.json").read_text(encoding="utf-8"))
    sdk = Path(os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT") or Path(os.environ["LOCALAPPDATA"]) / "Android/Sdk")
    tools = sdk / "build-tools/35.0.0"
    suffix = ".bat" if os.name == "nt" else ""
    with zipfile.ZipFile(args.apk) as apk:
        assert {p.split("/")[1] for p in apk.namelist() if p.startswith("lib/")} == {"arm64-v8a", "armeabi-v7a"}
    DIST.mkdir(exist_ok=True)
    env = dict(os.environ, NUSHU_LOCAL_STORE_PASSWORD=config["storePassword"], NUSHU_LOCAL_KEY_PASSWORD=config["keyPassword"])
    run(tools / ("apksigner" + suffix), "sign", "--ks", config["storeFile"], "--ks-key-alias", config["keyAlias"],
        "--ks-pass", "env:NUSHU_LOCAL_STORE_PASSWORD", "--key-pass", "env:NUSHU_LOCAL_KEY_PASSWORD", "--out", DIST / "NushuInput.apk", args.apk, env=env)
    run(tools / ("apksigner" + suffix), "verify", "--verbose", "--print-certs", DIST / "NushuInput.apk")


if __name__ == "__main__":
    main()
