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
    GENERATED_JSON_BUNDLE,
    export_all,
    generated_filename,
    load_config,
    render_coverage_matrix,
    render_generated_index,
    render_json_bundle,
    render_pack,
    render_pack_record,
    validate_config,
)
from audit_character_prompts import audit, render_report  # noqa: E402


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

    def test_json_render_has_prompt_metadata(self) -> None:
        record = render_pack_record(self.data, "furina_convention_phone")
        self.assertEqual(record["id"], "furina_convention_phone")
        self.assertEqual(record["character"]["id"], "furina")
        self.assertEqual(record["template"]["id"], "realistic_convention_phone")
        self.assertIn("主体锁定", record["prompt"])
        self.assertIn("非低俗", record["prompt"])
        bundle = json.loads(render_json_bundle(self.data))
        self.assertEqual(bundle["pack_count"], len(self.data["packs"]))
        self.assertEqual(len(bundle["packs"]), len(self.data["packs"]))
        self.assertIn("characters", bundle)

    def test_export_all_writes_expected_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            written = export_all(self.data, out_dir)
            expected_names = {"README.md", "覆盖矩阵.md", GENERATED_JSON_BUNDLE} | {
                generated_filename(pack["id"]) for pack in self.data["packs"]
            }
            self.assertEqual({path.name for path in written}, expected_names)
            self.assertEqual((out_dir / "README.md").read_text(encoding="utf-8"), render_generated_index(self.data))
            self.assertEqual((out_dir / "覆盖矩阵.md").read_text(encoding="utf-8"), render_coverage_matrix(self.data))
            self.assertEqual((out_dir / GENERATED_JSON_BUNDLE).read_text(encoding="utf-8"), render_json_bundle(self.data))
            for pack in self.data["packs"]:
                path = out_dir / generated_filename(pack["id"])
                self.assertEqual(path.read_text(encoding="utf-8"), render_pack(self.data, pack["id"], markdown=True))

    def test_generated_index_has_copy_entrypoints(self) -> None:
        index = render_generated_index(self.data)
        self.assertIn("快速复制入口", index)
        self.assertIn("按角色 × 用途", index)
        self.assertIn("furina_convention_phone.md", index)
        self.assertIn("citlali_readme_preview.md", index)
        self.assertIn("dori_character_card.md", index)

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

        json_output = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "build_prompt_pack.py"), "furina_convention_phone", "--format", "json"],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        payload = json.loads(json_output.stdout)
        self.assertEqual(payload["id"], "furina_convention_phone")
        self.assertIn("prompt", payload)

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

    def test_unified_quality_gate_help(self) -> None:
        result = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "run_quality_gate.py"), "--help"],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        self.assertIn("--refresh-generated", result.stdout)

    def test_character_audit_report_is_current(self) -> None:
        audit_result = audit(self.data)
        self.assertEqual(audit_result.errors, [])
        report_path = ROOT / "评估" / "角色防串审计报告.md"
        self.assertEqual(report_path.read_text(encoding="utf-8"), render_report(self.data))

    def test_character_audit_cli_check_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "audit_character_prompts.py"), "--check"],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        self.assertIn("OK：角色防串审计通过", result.stdout)

    def test_preview_manifest_matches_images(self) -> None:
        preview_dir = ROOT / "预览图"
        manifest_path = preview_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["$schema"], "manifest.schema.json")
        schema_path = preview_dir / manifest["$schema"]
        self.assertTrue(schema_path.exists())
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertIn("images", schema["properties"])
        self.assertIn("preview_image", schema["$defs"])
        manifest_files = {item["file"] for item in manifest["images"]}
        actual_files = {path.name for path in preview_dir.iterdir() if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}}
        self.assertEqual(manifest_files, actual_files)
        for item in manifest["images"]:
            self.assertTrue(item["public_safe"])
            self.assertIn(item["prompt_pack"], {pack["id"] for pack in self.data["packs"]})

    def test_gitignore_keeps_local_noise_out(self) -> None:
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for required in ["__pycache__/", "*.py[cod]", ".venv/", ".env", "原图/", "*.psd", ".DS_Store", "Thumbs.db"]:
            self.assertIn(required, gitignore)


if __name__ == "__main__":
    unittest.main()
