from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "工具"
sys.path.insert(0, str(TOOLS_DIR))

from build_prompt_pack import (  # noqa: E402
    DEFAULT_CONFIG,
    export_all,
    generated_filename,
    load_config,
    render_coverage_matrix,
    render_generated_index,
    render_pack,
    validate_config,
)


class PromptPackToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = load_config(DEFAULT_CONFIG)

    def test_schema_reference_exists(self) -> None:
        schema_ref = self.data.get("$schema")
        self.assertEqual(schema_ref, "prompt_packs.schema.json")
        schema_path = ROOT / "配置" / schema_ref
        self.assertTrue(schema_path.exists())
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertIn("characters", schema["properties"])
        self.assertIn("templates", schema["properties"])
        self.assertIn("packs", schema["properties"])
        self.assertIn("global_quality_constraints", schema["properties"])

    def test_config_is_valid(self) -> None:
        self.assertEqual(validate_config(self.data), [])

    def test_every_pack_renders_required_sections(self) -> None:
        required_terms = ["主体锁定", "必须保留", "安全约束", "防串约束", "质量约束", "非低俗", "不性感化", "不要混入"]
        for pack in self.data["packs"]:
            with self.subTest(pack=pack["id"]):
                rendered = render_pack(self.data, pack["id"])
                for term in required_terms:
                    self.assertIn(term, rendered)

    def test_markdown_render_has_title_and_code_block(self) -> None:
        pack = self.data["packs"][0]
        rendered = render_pack(self.data, pack["id"], markdown=True)
        self.assertTrue(rendered.startswith(f"# {pack['title']}\n"))
        self.assertIn("```text", rendered)
        self.assertTrue(rendered.rstrip().endswith("```"))

    def test_export_all_writes_expected_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            written = export_all(self.data, out_dir)
            expected_names = {"README.md", "覆盖矩阵.md"} | {generated_filename(pack["id"]) for pack in self.data["packs"]}
            self.assertEqual({path.name for path in written}, expected_names)
            self.assertEqual((out_dir / "README.md").read_text(encoding="utf-8"), render_generated_index(self.data))
            self.assertEqual((out_dir / "覆盖矩阵.md").read_text(encoding="utf-8"), render_coverage_matrix(self.data))
            for pack in self.data["packs"]:
                path = out_dir / generated_filename(pack["id"])
                self.assertEqual(path.read_text(encoding="utf-8"), render_pack(self.data, pack["id"], markdown=True))

    def test_coverage_matrix_lists_characters_and_templates(self) -> None:
        matrix = render_coverage_matrix(self.data)
        self.assertIn("Prompt Pack 覆盖矩阵", matrix)
        for character in self.data["characters"].values():
            self.assertIn(character["display_name"], matrix)
        for template in self.data["templates"].values():
            self.assertIn(template["task_type"], matrix)
        self.assertIn("当前缺口", matrix)

    def test_cli_list_and_validate(self) -> None:
        validate = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "build_prompt_pack.py"), "--validate"],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        self.assertIn("OK", validate.stdout)

        listing = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "build_prompt_pack.py"), "--list"],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        self.assertIn("furina_convention_phone", listing.stdout)
        self.assertIn("dori_commercial_poster", listing.stdout)

    def test_quality_gate_cli_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "check_prompt_repo.py")],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        self.assertIn("错误：0", result.stdout)


if __name__ == "__main__":
    unittest.main()
