import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
import yaml

spec = importlib.util.spec_from_file_location("installer", Path(__file__).resolve().parents[1] / "platforms/windows/install_user.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class ConfigurationTests(unittest.TestCase):
    def test_preserves_existing_schemas_and_other_patches(self):
        old = {"patch": {"schema_list": [{"schema": "terra_pinyin"}, {"schema": "nushu"}], "menu/page_size": 9}, "other": "keep"}
        merged = installer.merge_default(old, {})
        self.assertEqual([x["schema"] for x in merged["patch"]["schema_list"]], ["luna_pinyin_nushu", "nushu", "terra_pinyin"])
        self.assertEqual(merged["patch"]["menu/page_size"], 9)
        self.assertEqual(merged["other"], "keep")
        self.assertEqual(installer.merge_default(merged, {}), merged)
        self.assertEqual(old["patch"]["schema_list"][0]["schema"], "terra_pinyin")

    def test_uses_deployed_list_if_no_custom_list(self):
        result = installer.merge_default({}, {"schema_list": [{"schema": "cangjie5"}]})
        self.assertEqual(result["patch"]["schema_list"][-1], {"schema": "cangjie5"})

    def test_advanced_patch_is_rejected_without_silent_data_loss(self):
        with self.assertRaises(ValueError):
            installer.merge_default({"patch": {"schema_list/@next": {"schema": "terra"}}}, {})

    def test_backup_and_repeat_install_preserve_dictionaries(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            user, shared = root / "user", root / "shared"
            user.mkdir()
            shared.mkdir()
            (shared / "default.yaml").write_text("schema_list: [{schema: luna_pinyin}]", encoding="utf-8")
            (shared / "nushu.dict.yaml").write_text("incoming", encoding="utf-8")
            (shared / "luna_pinyin.dict.yaml").write_text("bundled common", encoding="utf-8")
            (user / "nushu.dict.yaml").write_text("old nushu", encoding="utf-8")
            (user / "luna_pinyin.dict.yaml").write_text("user common", encoding="utf-8")
            (user / "custom.userdb.txt").write_text("personal", encoding="utf-8")
            installer.configure(user, shared, root / "backup1")
            first = (user / "default.custom.yaml").read_text(encoding="utf-8")
            installer.configure(user, shared, root / "backup2")
            self.assertEqual((root / "backup1/nushu.dict.yaml").read_text(), "old nushu")
            self.assertEqual((user / "luna_pinyin.dict.yaml").read_text(), "user common")
            self.assertEqual((user / "custom.userdb.txt").read_text(), "personal")
            self.assertEqual((user / "default.custom.yaml").read_text(encoding="utf-8"), first)

    def test_invalid_configuration_changes_nothing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            user, shared = root / "user", root / "shared"
            user.mkdir()
            shared.mkdir()
            (user / "default.custom.yaml").write_text("patch: [invalid]", encoding="utf-8")
            (shared / "nushu.dict.yaml").write_text("incoming", encoding="utf-8")
            with self.assertRaises(ValueError):
                installer.configure(user, shared, root / "backup")
            self.assertFalse((user / "nushu.dict.yaml").exists())


if __name__ == "__main__":
    unittest.main()
