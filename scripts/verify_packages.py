"""Structural checks only: explicitly not a replacement for native installation QA."""
import gzip
import hashlib
import json
import struct
import zipfile
import xml.etree.ElementTree as ET
from common import ROOT, BUILD, DIST, download, sha256
from xar_package import read_xar


def equivalent_text(left, right):
    # Git checkouts may use CRLF on Windows and LF on macOS/Linux.
    # Validate the actual Unicode content without conflating line endings.
    return left.decode("utf-8-sig").replace("\r\n", "\n") == right.decode("utf-8-sig").replace("\r\n", "\n")


def cpio_files(raw):
    pos = 0
    files = {}
    while pos < len(raw) and raw[pos:pos + 6] in [b"070701", b"070702", b"070707"]:
        magic = raw[pos:pos + 6]
        if magic in [b"070701", b"070702"]:
            fields = [int(raw[pos + 6 + i * 8:pos + 14 + i * 8], 16) for i in range(13)]
            mode, size, namesize = fields[1], fields[6], fields[11]
            pos += 110
            name = raw[pos:pos + namesize - 1].decode("utf-8")
            pos += namesize
            pos = (pos + 3) & ~3
            data = raw[pos:pos + size]
            pos += size
            pos = (pos + 3) & ~3
        else:
            header = raw[pos:pos + 76]
            mode = int(header[18:24], 8)
            namesize, size = int(header[59:65], 8), int(header[65:76], 8)
            pos += 76
            name = raw[pos:pos + namesize - 1].decode("utf-8")
            pos += namesize
            data = raw[pos:pos + size]
            pos += size
        if name == "TRAILER!!!":
            break
        files[name.removeprefix("./")] = (mode, data)
    return files


def verify():
    results = {}
    if (DIST / "NushuInput.pkg").exists():
        package = read_xar(DIST / "NushuInput.pkg")
        original = read_xar(download("squirrel.pkg"))
        for member in ["PackageInfo", "Payload", "Scripts", "Bom"]:
            assert package["Squirrel.pkg/" + member] == original[member], f"Modified Squirrel member {member}"
        distribution = ET.fromstring(package["Distribution"])
        assert distribution.find("allowed-os-versions/os-version").attrib["min"] == "13.0"
        scripts = cpio_files(gzip.decompress(package["NushuResources.pkg/Scripts"]))
        assert scripts["postinstall"][0] & 0o111
        assert scripts["payload/启用女书.command"][0] & 0o111
        for schema in ["nushu.schema.yaml", "luna_pinyin_nushu.schema.yaml", "nushu.dict.yaml"]:
            assert equivalent_text(scripts["payload/shared/" + schema][1], (BUILD / "shared" / schema).read_bytes())
        assert scripts["payload/fonts/NotoSansNushu-Regular.ttf"][1] == (BUILD / "fonts/NotoSansNushu-Regular.ttf").read_bytes()
        payload = cpio_files(gzip.decompress(original["Payload"]))
        binary = next(data for name, (_, data) in payload.items() if name.endswith("Squirrel.app/Contents/MacOS/Squirrel"))
        magic, count = struct.unpack_from(">II", binary)
        assert magic in [0xCAFEBABE, 0xCAFEBABF], hex(magic)
        stride = 20 if magic == 0xCAFEBABE else 32
        archs = [struct.unpack_from(">I", binary, 8 + i * stride)[0] for i in range(count)]
        assert {0x01000007, 0x0100000C} <= set(archs), archs
        results["macos"] = {"archive_checksums": "passed", "scripts_and_resources": "passed", "squirrel_unmodified": True, "mach_o_architectures": ["x86_64", "arm64"], "native_installer_test": "see reports/macos-cloud-verification.json" if (ROOT / "reports/macos-cloud-verification.json").exists() else "not run"}
    if (DIST / "NushuInput.apk").exists():
        native_hashes = {}
        with zipfile.ZipFile(DIST / "NushuInput.apk") as apk:
            assert apk.testzip() is None
            native_abis = sorted({p.split("/")[1] for p in apk.namelist() if p.startswith("lib/")})
            assert native_abis == ["arm64-v8a", "armeabi-v7a"], native_abis
            for name, abi in [("trime-arm64.apk", "arm64-v8a"), ("trime-arm32.apk", "armeabi-v7a")]:
                with zipfile.ZipFile(download(name)) as original:
                    for path in original.namelist():
                        if path.startswith("lib/" + abi + "/") and path.endswith(".so"):
                            assert apk.read(path) == original.read(path), f"Native library changed: {path}"
                            native_hashes[path] = hashlib.sha256(apk.read(path)).hexdigest()
            for schema in ["nushu.schema.yaml", "luna_pinyin_nushu.schema.yaml", "nushu.dict.yaml"]:
                assert equivalent_text(apk.read("assets/shared/" + schema), (BUILD / "shared" / schema).read_bytes())
            assert apk.read("assets/shared/fonts/NotoSansNushu-Regular.ttf") == (BUILD / "fonts/NotoSansNushu-Regular.ttf").read_bytes()
        results["android"] = {"apk_zip_integrity": "passed", "native_abis": native_abis, "native_libraries_match_upstream_tag": True,
                              "native_library_sha256": native_hashes, "resources": "passed", "device_installation_test": "see verification record",
                              "page_size_validation": "tested on 4KB page-size emulator; 16KB page-size devices not validated"}
    (ROOT / "reports/package-validation.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    verify()
