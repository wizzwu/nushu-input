"""Native macOS pkgbuild/productbuild pipeline. Never modifies the signed Squirrel app."""
from pathlib import Path
import os
import plistlib
import shutil
import sys
import xml.etree.ElementTree as ET
import argparse
from common import ROOT, BUILD, DIST, run, download, copy_contents
from prepare import prepare


def stage():
    prepare()
    work = BUILD / "macos"
    scripts = work / "scripts"
    payload = scripts / "payload"
    payload.mkdir(parents=True, exist_ok=True)
    for name in ["shared", "fonts", "licenses"]:
        copy_contents(BUILD / name, payload / name)
    for name in ["configure.rb", "启用女书.command"]:
        shutil.copy2(ROOT / "platforms/macos" / name, payload / name)
    shutil.copy2(ROOT / "platforms/macos/postinstall", scripts / "postinstall")
    shutil.copy2(ROOT / "docs/使用说明.txt", payload / "使用说明.txt")
    shutil.copy2(BUILD / "resource-manifest.json", payload / "resource-manifest.json")
    for path in [scripts / "postinstall", payload / "启用女书.command"]:
        path.chmod(0o755)
    return work


def distribution(squirrel_id, squirrel_version):
    root = ET.Element("installer-gui-script", {"minSpecVersion": "2"})
    ET.SubElement(root, "title").text = "女书输入法 0.1.0 试用版"
    ET.SubElement(root, "options", {"customize": "never", "require-scripts": "false", "hostArchitectures": "x86_64,arm64"})
    allowed = ET.SubElement(root, "allowed-os-versions")
    ET.SubElement(allowed, "os-version", {"min": "13.0"})
    outline = ET.SubElement(root, "choices-outline")
    for choice, package, title in [("engine", squirrel_id, "鼠须管输入法"), ("nushu", "org.nushuinput.resources", "女书方案、字体及配置")]:
        ET.SubElement(outline, "line", {"choice": choice})
        node = ET.SubElement(root, "choice", {"id": choice, "visible": "false", "title": title, "start_selected": "true"})
        ET.SubElement(node, "pkg-ref", {"id": package})
    ET.SubElement(root, "pkg-ref", {"id": squirrel_id, "version": squirrel_version, "onConclusion": "RequireLogout"}).text = "#Squirrel.pkg"
    ET.SubElement(root, "pkg-ref", {"id": "org.nushuinput.resources", "version": "0.1.0"}).text = "#NushuResources.pkg"
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--portable", action="store_true", help="Generate unsigned flat package outside macOS; native verification still required")
    args = parser.parse_args()
    if args.portable:
        portable()
        return
    if sys.platform != "darwin":
        raise SystemExit("Mac installation package must be built/verified with macOS pkgbuild and productbuild. Use GitHub Actions.")
    work = stage()
    components = work / "components"
    components.mkdir(exist_ok=True)
    squirrel = download("squirrel.pkg")
    shutil.copy2(squirrel, components / "Squirrel.pkg")
    expanded = work / "squirrel-expanded"
    if not expanded.exists():
        run("pkgutil", "--expand", squirrel, expanded)
    info = ET.parse(expanded / "PackageInfo").getroot()
    (work / "Distribution.xml").write_bytes(distribution(info.attrib["identifier"], info.attrib["version"]))
    # Nopayload installs resources from the script archive. No bundle ownership or
    # upgrade receipt can cause pkgbuild to relocate a user's Rime directories.
    run("pkgbuild", "--nopayload", "--identifier", "org.nushuinput.resources", "--version", "0.1.0",
        "--scripts", work / "scripts", components / "NushuResources.pkg")
    DIST.mkdir(exist_ok=True)
    run("productbuild", "--distribution", work / "Distribution.xml", "--package-path", components, DIST / "NushuInput.pkg")
    verification = work / "verification"
    if not verification.exists():
        run("pkgutil", "--expand-full", DIST / "NushuInput.pkg", verification)
    squirrel_binary = next(verification.rglob("Squirrel.app/Contents/MacOS/Squirrel"))
    run("lipo", "-verify_arch", "x86_64", "arm64", squirrel_binary)
    run("codesign", "--verify", "--deep", "--strict", squirrel_binary.parents[2])
    # These validate the product and payload, not installation on a real Mac.
    print(DIST / "NushuInput.pkg")


def portable():
    from xar_package import read_xar, write_xar, cpio_gzip
    work = stage()
    original = read_xar(download("squirrel.pkg"))
    info = ET.fromstring(original["PackageInfo"])
    resources_info = ET.Element("pkg-info", {"format-version": "2", "identifier": "org.nushuinput.resources", "version": "0.1.0", "install-location": "/", "auth": "root"})
    scripts = ET.SubElement(resources_info, "scripts")
    ET.SubElement(scripts, "postinstall", {"file": "./postinstall"})
    entries = {"Distribution": distribution(info.attrib["identifier"], info.attrib["version"])}
    for name in ["PackageInfo", "Payload", "Scripts", "Bom"]:
        entries["Squirrel.pkg/" + name] = original[name]
    entries["NushuResources.pkg/PackageInfo"] = ET.tostring(resources_info, encoding="utf-8", xml_declaration=True)
    entries["NushuResources.pkg/Scripts"] = cpio_gzip(work / "scripts")
    DIST.mkdir(exist_ok=True)
    write_xar(DIST / "NushuInput.pkg", entries)
    print("Portable unsigned pkg generated. macOS Installer/native validation has NOT been run.")
    print(DIST / "NushuInput.pkg")


if __name__ == "__main__":
    main()
