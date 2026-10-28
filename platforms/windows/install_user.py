"""Runs as the invoking user, including when a different admin installs Weasel."""
from pathlib import Path
import ctypes
import datetime
import json
import os
import shutil
import subprocess
import sys
import traceback
import yaml

SCHEMAS = ["luna_pinyin_nushu", "nushu"]


def load_mapping(path):
    value = yaml.safe_load(path.read_text(encoding="utf-8-sig")) if path.exists() else {}
    if value is None:
        value = {}
    if not isinstance(value, dict):
        raise ValueError(f"配置不是 YAML 映射，已停止以保护原配置：{path}")
    return value


def merge_default(config, fallback):
    import copy
    config = copy.deepcopy(config)
    patch = config.setdefault("patch", {})
    if not isinstance(patch, dict):
        raise ValueError("patch 必须为映射，已停止以保护原配置")
    # Rime list patches can change their meaning if collapsed; stop instead of discarding them.
    if any(str(k).startswith("schema_list/") for k in patch):
        raise ValueError("检测到高级 schema_list 补丁，请先在输入法设置中启用女书；原配置未更改")
    old = patch.get("schema_list", fallback.get("schema_list", [])) or []
    if not isinstance(old, list):
        raise ValueError("schema_list 必须为列表")
    extra = [s for s in old if not isinstance(s, dict) or s.get("schema") not in SCHEMAS]
    patch["schema_list"] = [{"schema": s} for s in SCHEMAS] + extra
    return config


def configure(user_dir, shared, backup_root):
    """Validate every YAML change before modifying any files; back up overwritten files."""
    default = user_dir / "default.custom.yaml"
    fallback = load_mapping(user_dir / "build/default.yaml")
    if not fallback:
        fallback = load_mapping(shared / "default.yaml")
    merged = merge_default(load_mapping(default), fallback)
    writes = {default: yaml.safe_dump(merged, allow_unicode=True, sort_keys=False)}
    for schema in SCHEMAS:
        path = user_dir / f"{schema}.custom.yaml"
        cfg = load_mapping(path)
        patch = cfg.setdefault("patch", {})
        if not isinstance(patch, dict):
            raise ValueError(f"无效 patch：{path}")
        patch["style/font_face"] = "Noto Sans Nushu, Microsoft YaHei"
        patch["style/comment_font_face"] = "Microsoft YaHei"
        if schema == "luna_pinyin_nushu":
            patch["schema/name"] = "女书·普通话拼音"
        else:
            patch["schema/name"] = "女书·江永方言拼音"
        writes[path] = yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False)
    user_dir.mkdir(parents=True, exist_ok=True)
    backup_root.mkdir(parents=True, exist_ok=True)
    manifest = []
    incoming = [p for p in shared.rglob("*") if p.is_file()]
    for src in incoming:
        # Never replace a user's existing common dictionary or schema dependency.
        rel = src.relative_to(shared)
        dst = user_dir / rel
        owned = rel.name in ["nushu.dict.yaml", "nushu.schema.yaml", "luna_pinyin_nushu.schema.yaml", "s2nushu.txt", "s2nushu.json"]
        if dst.exists() and not owned:
            continue
        manifest.append((dst, src.read_bytes()))
    manifest.extend((p, text.encode("utf-8")) for p, text in writes.items())
    for dst, data in manifest:
        rel = dst.relative_to(user_dir)
        if dst.exists():
            backup = backup_root / rel
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dst, backup)
        dst.parent.mkdir(parents=True, exist_ok=True)
        temp = dst.with_name(dst.name + ".nushu-tmp")
        temp.write_bytes(data)
        temp.replace(dst)
    return backup_root


def registry_value(hive, key, name):
    import winreg
    for view in [winreg.KEY_WOW64_32KEY, winreg.KEY_WOW64_64KEY]:
        try:
            with winreg.OpenKey(hive, key, 0, winreg.KEY_READ | view) as h:
                value, _ = winreg.QueryValueEx(h, name)
                if value:
                    return os.path.expandvars(value)
        except FileNotFoundError:
            pass
    return None


def find_engine():
    import winreg
    root = registry_value(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Rime\Weasel", "InstallDir")
    if root:
        base = Path(root)
        if (base / "WeaselDeployer.exe").exists():
            return base
        candidates = sorted(base.glob("weasel-*/WeaselDeployer.exe"), key=lambda p: p.stat().st_mtime, reverse=True)
        if candidates:
            return candidates[0].parent
    return None


def install_engine(base):
    from ctypes import wintypes
    class SHELLEXECUTEINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("fMask", wintypes.ULONG), ("hwnd", wintypes.HWND),
                    ("lpVerb", wintypes.LPCWSTR), ("lpFile", wintypes.LPCWSTR), ("lpParameters", wintypes.LPCWSTR),
                    ("lpDirectory", wintypes.LPCWSTR), ("nShow", ctypes.c_int), ("hInstApp", wintypes.HINSTANCE),
                    ("lpIDList", ctypes.c_void_p), ("lpClass", wintypes.LPCWSTR), ("hkeyClass", wintypes.HKEY),
                    ("dwHotKey", wintypes.DWORD), ("hIcon", wintypes.HANDLE), ("hProcess", wintypes.HANDLE)]
    info = SHELLEXECUTEINFO()
    info.cbSize = ctypes.sizeof(info)
    info.fMask = 0x40  # SEE_MASK_NOCLOSEPROCESS
    info.lpVerb, info.lpFile, info.lpParameters, info.nShow = "runas", str(base / "weasel.exe"), "/S", 1
    if not ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(info)):
        raise ctypes.WinError()
    kernel = ctypes.windll.kernel32
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    try:
        kernel.WaitForSingleObject(info.hProcess, 0xFFFFFFFF)
        code = wintypes.DWORD()
        kernel.GetExitCodeProcess(info.hProcess, ctypes.byref(code))
        if code.value not in (0, 3010):
            raise RuntimeError(f"小狼毫安装失败或取消，退出码 {code.value}")
    finally:
        kernel.CloseHandle(info.hProcess)


def main():
    import winreg
    base = Path(__file__).resolve().parent
    engine = find_engine()
    if engine is None:
        install_engine(base)
        engine = find_engine()
    if engine is None:
        raise RuntimeError("未找到小狼毫，请查看安装日志")
    root = registry_value(winreg.HKEY_CURRENT_USER, r"Software\Rime\Weasel", "RimeUserDir")
    user_dir = Path(root) if root else Path(os.environ["APPDATA"]) / "Rime"
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = configure(user_dir, base / "shared", user_dir / "nushu-backups" / stamp)
    fonts = Path(os.environ["LOCALAPPDATA"]) / "Microsoft/Windows/Fonts"
    fonts.mkdir(parents=True, exist_ok=True)
    font = fonts / "NotoSansNushu-Regular.ttf"
    if not font.exists():
        shutil.copy2(base / "fonts/NotoSansNushu-Regular.ttf", font)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows NT\CurrentVersion\Fonts") as key:
        winreg.SetValueEx(key, "Noto Sans Nushu (TrueType)", 0, winreg.REG_SZ, str(font))
    ctypes.windll.gdi32.AddFontResourceW(str(font))
    ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001D, 0, 0, 2, 3000, None)
    # Deployer coordinates maintenance with a running Weasel service.
    subprocess.run([str(engine / "WeaselDeployer.exe"), "/deploy"], check=True, timeout=300)
    for schema in SCHEMAS:
        if not (user_dir / "build" / f"{schema}.schema.yaml").exists():
            raise RuntimeError(f"女书方案部署未完成：{schema}，备份位于 {backup}")
    subprocess.Popen([str(engine / "WeaselServer.exe")])
    (base / "install-result.json").write_text(json.dumps({"user_dir": str(user_dir), "backup": str(backup), "engine": str(engine)}, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    log = Path(os.environ.get("LOCALAPPDATA", ".")) / "NushuInput/install.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    try:
        with log.open("a", encoding="utf-8") as stream:
            sys.stdout = sys.stderr = stream
            print(datetime.datetime.now().isoformat(), "开始安装女书方案")
            main()
            print("安装完成")
    except Exception:
        with log.open("a", encoding="utf-8") as stream:
            traceback.print_exc(file=stream)
        ctypes.windll.user32.MessageBoxW(None, f"安装未完成。原配置的备份保存在 Rime/nushu-backups。\n详情请查看：{log}", "女书输入法", 0x10)
        sys.exit(1)
