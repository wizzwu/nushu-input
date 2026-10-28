"""Build modified Trime sources with the exact tag's unmodified native libraries."""
from pathlib import Path
import argparse
import io
import json
import os
import re
import secrets
import shutil
import subprocess
import tarfile
import zipfile
import yaml
from common import ROOT, BUILD, DIST, LOCK, run, source, download, copy_contents
from prepare import prepare


def replace(path, old, new):
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"Upstream changed; patch did not match: {path}: {old[:70]}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def prepare_android():
    prepare()
    src = source("trime")
    dest = BUILD / "android"
    dest.mkdir(exist_ok=True)
    data = subprocess.check_output(["git", "-C", str(src), "archive", "HEAD"])
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        archive.extractall(dest, filter="data")
    wrapper = dest / "gradle/wrapper/gradle-wrapper.properties"
    wrapper.write_text(wrapper.read_text(encoding="utf-8") + "\ndistributionSha256Sum=8d97a97984f6cbd2b85fe4c60a743440a347544bf18818048e611f5288d46c94\n", encoding="utf-8")
    gradle = dest / "app/build.gradle.kts"
    replace(gradle, '    id("com.osfans.trime.native-app-convention")\n', '    alias(libs.plugins.android.application)\n')
    replace(gradle, '    id("com.osfans.trime.native-cache-hash")\n', "")
    replace(gradle, '    id("com.osfans.trime.opencc-data")\n', "")
    replace(gradle, 'applicationId = "com.osfans.trime"', 'applicationId = "org.nushuinput.trial"')
    replace(gradle, 'minSdk = 21', 'minSdk = 26')
    replace(gradle, 'versionCode = 20250501', 'versionCode = 100')
    replace(gradle, 'versionName = "3.3.4"', 'versionName = "0.1.0"')
    replace(gradle, '        multiDexEnabled = true', '''        buildConfigField("String", "LIBRIME_VERSION", "\\\"1c233581\\\"")
        buildConfigField("String", "OPENCC_VERSION", "\\\"556ed224\\\"")
        multiDexEnabled = true''')
    replace(gradle, '    packaging {', '''    sourceSets.getByName("main").jniLibs.srcDir("prebuilt")
    packaging {
        jniLibs { useLegacyPackaging = true }''')
    # Keep JNI classes in com.osfans.trime; the application ID is independent.
    manifest = dest / "app/src/main/AndroidManifest.xml"
    text = manifest.read_text(encoding="utf-8")
    for permission in ["READ_EXTERNAL_STORAGE", "WRITE_EXTERNAL_STORAGE", "MANAGE_EXTERNAL_STORAGE"]:
        text = re.sub(r'\s*<uses-permission android:name="android.permission.' + permission + r'"\s*/>', '', text)
    text = re.sub(r'android:(name|targetActivity)="\.', r'android:\1="com.osfans.trime.', text)
    manifest.write_text(text, encoding="utf-8")
    java = dest / "app/src/main/java/com/osfans/trime"
    application = java / "TrimeApplication.kt"
    replace(application, 'import com.osfans.trime.data.db.ClipboardHelper', 'import com.osfans.trime.data.base.DataManager\nimport com.osfans.trime.data.db.ClipboardHelper')
    replace(application, '                ThemeManager.init(resources.configuration)', '                DataManager.sync()\n                ThemeManager.init(resources.configuration)')
    manager = java / "data/base/DataManager.kt"
    replace(manager, 'File(Environment.getExternalStorageDirectory(), "rime")', 'File(appContext.getExternalFilesDir(null), "rime")')
    replace(manager, 'Timber.d("Created empty default.custom.yaml")', '''File(userDataDir, DEFAULT_CUSTOM_FILE_NAME).writeText(
                        appContext.assets.open("nushu-default.custom.yaml").bufferedReader().use { it.readText() }
                    )
                    Timber.d("Created Nushu default.custom.yaml")''')
    replace(manager, '            Timber.d("Synced!")', '''            val nushuFont = File(userDataDir, "fonts/NotoSansNushu-Regular.ttf")
            if (!nushuFont.exists()) {
                nushuFont.parentFile?.mkdirs()
                File(sharedDataDir, "fonts/NotoSansNushu-Regular.ttf").copyTo(nushuFont)
            }
            Timber.d("Synced!")''')
    permissions = java / "util/Permissions.kt"
    replace(permissions, '''    XXPermissions.isGranted(this, Permission.MANAGE_EXTERNAL_STORAGE) &&
        Environment.getExternalStorageDirectory().absolutePath.isNotEmpty()''', '    getExternalFilesDir(null) != null')
    # Existing setup detects the private directory as available and skips storage access.
    # A profile folder picker would permit accidental sharing with an existing Trime.
    profile_xml = dest / "app/src/main/res/xml/profile_preference.xml"
    text = profile_xml.read_text(encoding="utf-8")
    text = re.sub(r'\s*<com.osfans.trime.ui.components.FolderPickerPreference\b.*?/>', '', text, flags=re.S)
    profile_xml.write_text(text, encoding="utf-8")
    assets = dest / "app/src/main/assets"
    shared = assets / "shared"
    copy_contents(BUILD / "shared", shared)
    copy_contents(BUILD / "fonts", shared / "fonts")
    copy_contents(BUILD / "licenses", assets / "licenses")
    shutil.copy2(src / "LICENSE", assets / "licenses/Trime-GPL-3.0.txt")
    cfg = {"patch": {"schema_list": [{"schema": "luna_pinyin_nushu"}, {"schema": "nushu"}]}}
    (assets / "nushu-default.custom.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")
    for schema, name in [("luna_pinyin_nushu", "女书·普通话拼音"), ("nushu", "女书·江永方言拼音")]:
        (shared / f"{schema}.custom.yaml").write_text(yaml.safe_dump({"patch": {"schema/name": name}}, allow_unicode=True), encoding="utf-8")
    for theme_path in [shared / "trime.yaml", shared / "tongwenfeng.trime.yaml"]:
        # Preserve lexical scalars: color strings such as 0xffeeeeee must not
        # become decimal integers when passed to Android's theme color parser.
        theme = yaml.load(theme_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        theme["style"]["candidate_font"] = ["NotoSansNushu-Regular.ttf"]
        theme["style"]["text_font"] = ["NotoSansNushu-Regular.ttf"]
        theme.setdefault("preset_keys", {})["Nushu_toggle"] = {"label": "汉/女", "send": "Control+Shift+4"}
        for keyboard in theme.get("preset_keyboards", {}).values():
            for key in keyboard.get("keys", []):
                if key.get("click") in ["space", "space1"]:
                    key["long_click"] = "Nushu_toggle"
                    key["hint"] = "汉字/女书"
                if key.get("click") == "Return":
                    key["long_click"] = "Menu"
                if key.get("click") == "Mode_switch":
                    key["click"] = "Nushu_toggle"
                    key["long_click"] = "Mode_switch"
        display_replacements = {"全選": "全选", "複製": "复制", "貼上": "粘贴", "剪下": "剪切", "數字": "数字",
                                "符號": "符号", "隱藏": "隐藏", "時間": "时间", "鍵盤": "键盘", "簡體": "简体",
                                "繁體": "繁体", "漢字": "汉字", "選單": "菜单", "選擇": "选择", "設置": "设置",
                                "編碼": "编码", "註釋": "注释", "預設": "默认", "標準": "标准"}
        def localize(node):
            if isinstance(node, list):
                for value in node:
                    localize(value)
            elif isinstance(node, dict):
                for key, value in node.items():
                    if key in ["label", "name", "hint", "tips"] and isinstance(value, str):
                        for before, after in display_replacements.items():
                            value = value.replace(before, after)
                        node[key] = value
                    else:
                        localize(value)
        localize(theme)
        theme_path.write_text(yaml.safe_dump(theme, allow_unicode=True, sort_keys=False), encoding="utf-8")
        def resolve(node):
            if isinstance(node, list):
                return [resolve(value) for value in node]
            if not isinstance(node, dict):
                return node
            result = {}
            if "__include" in node:
                path = node["__include"]
                if not path.startswith("/"):
                    raise RuntimeError(f"Unexpected external theme include: {path}")
                value = theme
                for part in path.strip("/").split("/"):
                    value = value[part]
                result.update(resolve(value))
            result.update({key: resolve(value) for key, value in node.items() if key != "__include"})
            return result
        # ThemeManager starts before the Rime dispatcher on a clean installation.
        # Ship a resolved fallback so keyboard creation never races first deployment.
        initial = shared / "build" / theme_path.name
        initial.parent.mkdir(exist_ok=True)
        initial.write_text(yaml.safe_dump(resolve(theme), allow_unicode=True, sort_keys=False), encoding="utf-8")
    # Every locale uses the product name while retaining upstream credits in About.
    for res in (dest / "app/src/main/res").glob("values*/strings.xml"):
        text = res.read_text(encoding="utf-8")
        for key in ["app_name_release", "app_name_debug", "trime_app_slogan"]:
            text = re.sub(r'(<string name="' + key + r'"[^>]*>).*?(</string>)', r'\g<1>女书输入法\2', text, flags=re.S)
        res.write_text(text, encoding="utf-8")
    for name, abi in [("trime-arm64.apk", "arm64-v8a"), ("trime-arm32.apk", "armeabi-v7a")]:
        with zipfile.ZipFile(download(name)) as apk:
            native = [p for p in apk.namelist() if p.startswith(f"lib/{abi}/") and p.endswith(".so")]
            if not native:
                raise RuntimeError(f"No native libraries in {name}")
            for path in native:
                target = dest / "app/prebuilt" / abi / Path(path).name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(apk.read(path))
    # Symlink stubs from a Windows checkout must never be packaged as YAML files.
    for p in shared.glob("*.yaml"):
        if p.read_text(encoding="utf-8").strip().startswith("../prelude/"):
            raise RuntimeError(f"Unresolved upstream symlink: {p}")
    sdk = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if not sdk and os.name == "nt":
        sdk = str(Path(os.environ["LOCALAPPDATA"]) / "Android/Sdk")
    if sdk:
        (dest / "local.properties").write_text("sdk.dir=" + sdk.replace("\\", "/").replace(":", "\\:") + "\n", encoding="utf-8")
    return dest


def signing(dest):
    supplied = os.environ.get("NUSHU_KEYSTORE")
    if supplied:
        config = {"storeFile": supplied, "storePassword": os.environ["NUSHU_STORE_PASSWORD"],
                  "keyPassword": os.environ["NUSHU_KEY_PASSWORD"], "keyAlias": os.environ.get("NUSHU_KEY_ALIAS", "nushu-trial")}
    else:
        if os.environ.get("CI"):
            raise RuntimeError("CI signing key missing; refusing to generate a replacement identity")
        private = Path.home() / ".codex/secrets/nushu-input"
        private.mkdir(parents=True, exist_ok=True)
        config_path = private / "signing.json"
        if config_path.exists():
            config = json.loads(config_path.read_text(encoding="utf-8"))
        else:
            password = secrets.token_urlsafe(32)
            config = {"storeFile": str(private / "nushu-trial.jks"), "storePassword": password, "keyPassword": password, "keyAlias": "nushu-trial"}
            env = dict(os.environ, NUSHU_TEMP_PASSWORD=password)
            run(Path(os.environ["JAVA_HOME"]) / "bin" / ("keytool.exe" if os.name == "nt" else "keytool"),
                "-genkeypair", "-keystore", config["storeFile"], "-storetype", "PKCS12", "-alias", config["keyAlias"],
                "-storepass:env", "NUSHU_TEMP_PASSWORD", "-keypass:env", "NUSHU_TEMP_PASSWORD", "-keyalg", "RSA",
                "-keysize", "3072", "-validity", "10000", "-dname", "CN=Nushu Input Trial", env=env)
            config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        backup = private / "backup"
        backup.mkdir(exist_ok=True)
        shutil.copy2(config["storeFile"], backup / Path(config["storeFile"]).name)
        shutil.copy2(config_path, backup / "signing.json")
    # keystore.properties is generated only in the ignored build directory.
    lines = [f"{k}={v.replace(chr(92), '/')}" for k, v in config.items()]
    (dest / "keystore.properties").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--unsigned", action="store_true", help="Build a CI APK for signing locally; never generate or upload a CI private key")
    args = parser.parse_args()
    dest = prepare_android()
    if args.prepare_only:
        return
    if args.unsigned:
        (dest / "keystore.properties").unlink(missing_ok=True)
    else:
        signing(dest)
    env = dict(os.environ, BUILD_VERSION_NAME="0.1.0", BUILD_GIT_REPO="https://github.com/wizzwu/todo", CI_NAME="NushuInput",
               BUILD_COMMIT_HASH=LOCK["sources"]["trime"]["commit"])
    if os.name == "nt":
        cmd = ["cmd", "/c", "gradlew.bat"]
    else:
        cmd = ["bash", "gradlew"]
    run(*cmd, ":app:assembleRelease", "--no-daemon", "--console=plain", cwd=dest, env=env)
    apks = list((dest / "app/build/outputs/apk/release").glob("*.apk"))
    apks = [p for p in apks if p.name.endswith("-unsigned.apk") == args.unsigned]
    if len(apks) != 1:
        raise RuntimeError(f"Expected one universal APK, got {apks}")
    with zipfile.ZipFile(apks[0]) as apk:
        for abi in ["arm64-v8a", "armeabi-v7a"]:
            assert any(p.startswith(f"lib/{abi}/") for p in apk.namelist()), abi
    DIST.mkdir(exist_ok=True)
    target = DIST / ("NushuInput-unsigned.apk" if args.unsigned else "NushuInput.apk")
    shutil.copy2(apks[0], target)
    print(target)


if __name__ == "__main__":
    main()
