from pathlib import Path
import csv
import json
import yaml
from fontTools.ttLib import TTFont
from common import ROOT, BUILD, LOCK, sha256


def validate():
    shared = BUILD / "shared"
    expected = set(range(0x1B170, 0x1B2FC))
    rows = []
    dictionary = (shared / "nushu.dict.yaml").read_text(encoding="utf-8-sig").split("...", 1)[1]
    for line in dictionary.splitlines():
        if line.strip() and not line.startswith("#"):
            char, code, *_ = line.split("\t")
            rows.append((char, code))
    actual = {ord(char) for char, _ in rows if len(char) == 1}
    assert actual == expected, f"Dictionary missing={expected - actual}, unexpected={actual - expected}"
    font = TTFont(BUILD / "fonts/NotoSansNushu-Regular.ttf")
    cmap = font.getBestCmap()
    assert expected <= set(cmap), "Font missing Nushu characters"
    font.close()
    for path in shared.glob("*.schema.yaml"):
        schema = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
        assert isinstance(schema, dict), f"Invalid schema {path}"
        for dependency in schema.get("schema", {}).get("dependencies", []):
            assert (shared / f"{dependency}.schema.yaml").exists(), f"Missing dependency: {dependency}"
    differences = []
    readings = {}
    with (ROOT / "upstream/unicode_nushu/data.csv").open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.reader(stream):
            if row and len(row[0]) == 1 and ord(row[0]) in expected:
                readings[row[0]] = row[3]
    for char, code in rows:
        reference = readings.get(char)
        if reference != code:
            differences.append({"character": char, "codepoint": f"U+{ord(char):X}", "input_reading": code, "reference_reading": reference})
    mapped = set()
    mappings = []
    for line in (shared / "opencc/s2nushu.txt").read_text(encoding="utf-8-sig").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        key, val = line.split("\t", 1)
        for char in val:
            if 0x1B170 <= ord(char) <= 0x1B2FF:
                assert ord(char) in expected
                mapped.add(ord(char))
                mappings.append((key, char))
    manifest = json.loads((BUILD / "resource-manifest.json").read_text(encoding="utf-8"))
    for name, digest in manifest["resources"].items():
        assert sha256(BUILD / name) == digest, name
    report = {"dictionary_unique_characters": len(actual), "font_covered_characters": len(expected),
              "opencc_reachable_characters": len(mapped), "reference_characters": len(readings),
              "reading_differences": differences, "policy": "Report differences; preserve upstream mappings and readings."}
    report_dir = ROOT / "reports"
    report_dir.mkdir(exist_ok=True)
    (report_dir / "data-validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "reading_differences"}, ensure_ascii=False))
    print(f"Reading differences: {len(differences)}")
    return report


if __name__ == "__main__":
    validate()
