"""Record evidence from the explicit, temporary emulator used for acceptance tests."""
from pathlib import Path
import argparse
import json
import os
import subprocess
from common import ROOT, DIST, sha256


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serial", required=True)
    args = parser.parse_args()
    if not args.serial.startswith("emulator-"):
        raise SystemExit("This recorder is restricted to temporary emulator instances")
    sdk = Path(os.environ.get("ANDROID_HOME") or Path(os.environ["LOCALAPPDATA"]) / "Android/Sdk")
    adb = sdk / "platform-tools" / ("adb.exe" if os.name == "nt" else "adb")
    def query(*cmd):
        return subprocess.check_output([str(adb), "-s", args.serial, *cmd], encoding="utf-8", errors="replace").strip()
    pid = query("shell", "pidof", "org.nushuinput.smoketest")
    logs = query("logcat", "-d", "--pid=" + pid, "-s", "NushuFixture:I", "*:S")
    assert "U+1B181" in logs and "U+5973" in logs and "U+1B2E4" in logs, logs
    assert "CLIPBOARD_ROUNDTRIP=true" in logs
    wifi = query("shell", "cmd", "wifi", "status")
    mobile = query("shell", "settings", "get", "global", "mobile_data")
    assert "disabled" in wifi.lower() and mobile == "0"
    marker = query("shell", "cat", "/sdcard/Android/data/org.nushuinput.trial/files/rime/nushu-qa-marker.txt")
    assert marker == "nushu-upgrade-preservation"
    report = {"date": "2026-10-28", "apk_sha256": sha256(DIST / "NushuInput.apk"), "environment": {
        "android_release": query("shell", "getprop", "ro.build.version.release"),
        "sdk": query("shell", "getprop", "ro.build.version.sdk"),
        "emulator_abi_list": query("shell", "getprop", "ro.product.cpu.abilist"),
        "page_size": int(query("shell", "getconf", "PAGE_SIZE")), "wifi": "disabled", "mobile_data": "disabled",
        "physical_device": False, "arm_execution": "ARM64 binary on emulator ARM translation"},
        "verified": ["clean offline install and first deployment", "nv -> U+1B181", "touch Hanzi/Nushu switch -> U+5973",
                     "Jiangyong schema input i -> U+1B2E4", "clipboard roundtrip preserves Unicode", "in-place APK upgrade preserves user-directory marker"],
        "fixture_log": logs, "limitations": ["No physical ARM device tested", "No 16KB page-size device tested", "Android 8 minimum declared; not tested on an Android 8 device"]}
    (ROOT / "reports/android-offline-verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Recorded offline input, clipboard and upgrade verification")


if __name__ == "__main__":
    main()
