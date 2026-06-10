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
    DEFAULT_TAG_TAXONOMY,
    GENERATED_CSV_INDEX,
    GENERATED_JSON_BUNDLE,
    GENERATED_JSON_BUNDLE_SCHEMA,
    GENERATED_TAG_COVERAGE_MATRIX,
    GENERATED_TAG_INDEX,
    config_digest,
    export_all,
    generated_filename,
    load_config,
    load_tag_taxonomy,
    render_coverage_matrix,
    render_csv_index,
    render_generated_index,
    render_json_bundle,
    render_pack,
    render_pack_record,
    render_tag_coverage_matrix,
    render_tag_index,
    validate_config,
    validate_tag_taxonomy,
)
from build_project_dashboard import (  # noqa: E402
    render_dashboard as render_project_dashboard,
)
from audit_character_prompts import audit, render_report  # noqa: E402
from check_prompt_repo import (  # noqa: E402
    SECRET_PATTERNS,
    classify_orientation,
    image_dimensions,
    reduced_aspect_ratio,
)
from lint_prompt_quality import (  # noqa: E402
    lint as lint_prompt_quality,
    load_rules,
    render_report as render_prompt_quality_report,
)
from new_output_evaluation import (  # noqa: E402
    build_document as build_output_evaluation_document,
    build_record as build_output_evaluation_record,
    parse_scores as parse_output_evaluation_scores,
)
from sync_preview_manifest import (  # noqa: E402
    render_manifest as render_preview_manifest,
    sync_manifest,
)
from summarize_output_evaluations import (  # noqa: E402
    render_summary as render_output_evaluation_summary,
)
from suggest_failure_fixes import render_fix_suggestions  # noqa: E402
from validate_failure_fix_lexicon import (  # noqa: E402
    load_json as load_failure_fix_json,
    render_markdown as render_failure_fix_markdown,
    validate_document as validate_failure_fix_document,
)
from validate_output_evaluations import (  # noqa: E402
    load_json as load_evaluation_json,
    validate_document as validate_evaluation_document,
)
from validate_gpt_image2_parameters import (  # noqa: E402
    RECOMMENDED_PROFILES,
    is_near_9_16,
    parse_size_spec,
    render_markdown as render_gpt_image2_size_markdown,
    validate_size_spec,
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
        self.assertIn("tags", schema["$defs"]["template"]["properties"])

        taxonomy = load_tag_taxonomy(DEFAULT_TAG_TAXONOMY)
        self.assertEqual(taxonomy.get("$schema"), "tag_taxonomy.schema.json")
        taxonomy_schema_path = ROOT / "配置" / taxonomy["$schema"]
        self.assertTrue(taxonomy_schema_path.exists())
        taxonomy_schema = json.loads(taxonomy_schema_path.read_text(encoding="utf-8"))
        self.assertIn("tags", taxonomy_schema["properties"])

    def test_config_is_valid(self) -> None:
        self.assertEqual(validate_config(self.data), [])

    def test_tag_taxonomy_covers_template_tags(self) -> None:
        taxonomy = load_tag_taxonomy(DEFAULT_TAG_TAXONOMY)
        self.assertEqual(validate_tag_taxonomy(taxonomy), [])
        known_tags = {tag["id"] for tag in taxonomy["tags"]}
        used_tags = {tag for template in self.data["templates"].values() for tag in template["tags"]}
        self.assertTrue(used_tags <= known_tags)
        self.assertIn("公开安全", known_tags)

    def test_config_rejects_unknown_or_alias_tags(self) -> None:
        mutated = json.loads(json.dumps(self.data, ensure_ascii=False))
        mutated["templates"]["commercial_poster"]["tags"].append("商业海报图")
        errors = validate_config(mutated)
        self.assertTrue(any("请改为正式标签 商业海报" in error for error in errors))

        mutated = json.loads(json.dumps(self.data, ensure_ascii=False))
        mutated["templates"]["commercial_poster"]["tags"].append("未登记标签")
        errors = validate_config(mutated)
        self.assertTrue(any("未登记到 配置/tag_taxonomy.json：未登记标签" in error for error in errors))

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
        self.assertIn("tags", record)
        self.assertIn("写实cos", record["tags"])
        self.assertIn("tags", record["template"])
        self.assertIn("主体锁定", record["prompt"])
        self.assertIn("非低俗", record["prompt"])
        bundle = json.loads(render_json_bundle(self.data))
        self.assertEqual(bundle["$schema"], GENERATED_JSON_BUNDLE_SCHEMA)
        self.assertEqual(bundle["source_config"], "配置/prompt_packs.json")
        self.assertEqual(bundle["source_config_sha256"], config_digest(self.data))
        self.assertEqual(bundle["generator"], "工具/build_prompt_pack.py")
        self.assertEqual(bundle["pack_count"], len(self.data["packs"]))
        self.assertEqual(len(bundle["packs"]), len(self.data["packs"]))
        self.assertIn("characters", bundle)
        schema = json.loads((ROOT / "生成提示词" / GENERATED_JSON_BUNDLE_SCHEMA).read_text(encoding="utf-8"))
        self.assertIn("source_config_sha256", schema["properties"])
        self.assertIn("generator", schema["properties"])
        self.assertIn("generated_pack", schema["$defs"])

    def test_export_all_writes_expected_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            written = export_all(self.data, out_dir)
            expected_names = {
                "README.md",
                "覆盖矩阵.md",
                GENERATED_TAG_INDEX,
                GENERATED_TAG_COVERAGE_MATRIX,
                GENERATED_JSON_BUNDLE,
                GENERATED_CSV_INDEX,
            } | {
                generated_filename(pack["id"]) for pack in self.data["packs"]
            }
            self.assertEqual({path.name for path in written}, expected_names)
            self.assertEqual((out_dir / "README.md").read_text(encoding="utf-8"), render_generated_index(self.data))
            self.assertEqual((out_dir / "覆盖矩阵.md").read_text(encoding="utf-8"), render_coverage_matrix(self.data))
            self.assertEqual((out_dir / GENERATED_TAG_INDEX).read_text(encoding="utf-8"), render_tag_index(self.data))
            self.assertEqual((out_dir / GENERATED_TAG_COVERAGE_MATRIX).read_text(encoding="utf-8"), render_tag_coverage_matrix(self.data))
            self.assertEqual((out_dir / GENERATED_JSON_BUNDLE).read_text(encoding="utf-8"), render_json_bundle(self.data))
            self.assertEqual((out_dir / GENERATED_CSV_INDEX).read_text(encoding="utf-8"), render_csv_index(self.data))
            for pack in self.data["packs"]:
                path = out_dir / generated_filename(pack["id"])
                self.assertEqual(path.read_text(encoding="utf-8"), render_pack(self.data, pack["id"], markdown=True))

    def test_generated_index_has_copy_entrypoints(self) -> None:
        index = render_generated_index(self.data)
        self.assertIn("快速复制入口", index)
        self.assertIn("按角色 × 用途", index)
        self.assertIn(GENERATED_JSON_BUNDLE_SCHEMA, index)
        self.assertIn("furina_convention_phone.md", index)
        self.assertIn("citlali_readme_preview.md", index)
        self.assertIn("dori_character_card.md", index)
        self.assertIn(GENERATED_TAG_INDEX, index)
        self.assertIn(GENERATED_TAG_COVERAGE_MATRIX, index)
        self.assertIn(GENERATED_CSV_INDEX, index)

    def test_tag_index_groups_prompt_packs(self) -> None:
        tag_index = render_tag_index(self.data)
        self.assertIn("Prompt Pack 标签索引", tag_index)
        self.assertIn("`公开安全`", tag_index)
        self.assertIn("`商业海报`", tag_index)
        self.assertIn("furina_commercial_poster.md", tag_index)

    def test_tag_coverage_matrix_counts_characters_and_templates(self) -> None:
        matrix = render_tag_coverage_matrix(self.data)
        self.assertIn("Prompt Pack 标签覆盖矩阵", matrix)
        self.assertIn("`公开安全`", matrix)
        self.assertIn("公开安全", matrix)
        self.assertIn("芙宁娜 Furina", matrix)
        self.assertIn("茜特菈莉 Citlali", matrix)
        self.assertIn("多莉 Dori", matrix)
        self.assertIn("commercial_poster", matrix)
        self.assertIn("未使用的正式标签", matrix)

    def test_csv_index_lists_prompt_pack_files(self) -> None:
        csv_text = render_csv_index(self.data)
        self.assertIn("id,title,character_id,character,template_id,template_type,tags,file", csv_text)
        self.assertIn("furina_convention_phone", csv_text)
        self.assertIn("furina_convention_phone.md", csv_text)
        self.assertIn("写实cos;手机随手拍", csv_text)
        self.assertIn("茜特菈莉 Citlali", csv_text)

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

        tag_output = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "build_prompt_pack.py"), "--tag", "商业海报"],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        self.assertIn("furina_commercial_poster", tag_output.stdout)
        self.assertIn("dori_commercial_poster", tag_output.stdout)

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

    def test_gpt_image2_size_profiles_are_valid(self) -> None:
        self.assertEqual(parse_size_spec("1024x1824"), (1024, 1824))
        self.assertTrue(is_near_9_16(1024, 1824))

        for profile in RECOMMENDED_PROFILES:
            with self.subTest(profile=profile.name):
                result = validate_size_spec(profile.size, require_9_16=True)
                self.assertEqual(result.errors, ())
                self.assertEqual(result.warnings, ())
                self.assertTrue(result.is_near_9_16)

        fallback = validate_size_spec("1024x1536", require_9_16=True)
        self.assertEqual(fallback.errors, ())
        self.assertIn("2:3", fallback.warnings[0])

        invalid = validate_size_spec("1080x1920", require_9_16=True)
        self.assertIn("width 不是 16 的倍数", invalid.errors)

    def test_gpt_image2_parameter_cli_check_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "validate_gpt_image2_parameters.py"), "--check"],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        self.assertIn("1024x1824", result.stdout)

        markdown = render_gpt_image2_size_markdown()
        self.assertIn("gpt-image-2 推荐尺寸档位自检", markdown)
        self.assertIn("1024x1536", markdown)

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

    def test_prompt_quality_report_is_current(self) -> None:
        rules = load_rules()
        result = lint_prompt_quality(self.data, rules)
        self.assertEqual(result.errors, [])
        report_path = ROOT / "评估" / "Prompt文本质量审计报告.md"
        self.assertEqual(report_path.read_text(encoding="utf-8"), render_prompt_quality_report(self.data, rules))

    def test_prompt_quality_cli_check_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "lint_prompt_quality.py"), "--check"],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        self.assertIn("OK：Prompt 文本质量审计通过", result.stdout)

    def test_failure_fix_lexicon_is_valid_and_markdown_current(self) -> None:
        document = load_failure_fix_json(ROOT / "评估" / "failure_fix_lexicon.json")
        result = validate_failure_fix_document(document, self.data)
        self.assertEqual(result.errors, [])
        self.assertEqual(len(document["rules"]), 11)
        self.assertIn("furina_contamination", {rule["id"] for rule in document["rules"]})
        self.assertIn("composition_ratio_mismatch", {rule["id"] for rule in document["rules"]})
        report_path = ROOT / "评估" / "失败修正词库.md"
        self.assertEqual(report_path.read_text(encoding="utf-8"), render_failure_fix_markdown(document))

    def test_failure_fix_lexicon_cli_check_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "validate_failure_fix_lexicon.py"), "--check"],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        self.assertIn("OK：失败修正词库校验通过", result.stdout)

    def test_output_evaluation_example_is_valid(self) -> None:
        document = load_evaluation_json(ROOT / "评估" / "output_evaluations.example.json")
        result = validate_evaluation_document(document, self.data)
        self.assertEqual(result.errors, [])
        self.assertEqual(len(document["evaluations"]), 1)
        self.assertEqual(document["evaluations"][0]["failure_ids"], ["composition_ratio_mismatch"])

    def test_new_output_evaluation_builder_creates_valid_document(self) -> None:
        scores = parse_output_evaluation_scores(
            [
                "role_consistency=23",
                "composition_ratio=11",
                "material_detail=13",
                "scene_match=9",
                "public_safety=15",
                "text_ui=10",
                "delivery_usefulness=8",
            ]
        )
        record = build_output_evaluation_record(
            self.data,
            "furina_readme_preview",
            "预览图/furina-dessert-01.jpg",
            record_id="preview-furina-dessert-builder",
            record_date="2026-06-10",
            scores=scores,
            public_safe=True,
            decision="keep",
            failure_ids=["composition_ratio_mismatch"],
            issues=["README 样张为横向展示图。"],
            next_action="作为 README 公开预览样张保留。",
            notes="单元测试生成的评分记录。",
        )
        self.assertEqual(record["character"], "furina")
        self.assertEqual(record["total_score"], 89)
        document = build_output_evaluation_document([record], version="test-output-evaluations")
        result = validate_evaluation_document(document, self.data)
        self.assertEqual(result.errors, [])

    def test_new_output_evaluation_cli_outputs_document(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(TOOLS_DIR / "new_output_evaluation.py"),
                "--prompt-pack",
                "furina_readme_preview",
                "--image-file",
                "预览图/furina-dessert-01.jpg",
                "--id",
                "preview-furina-dessert-cli",
                "--date",
                "2026-06-10",
                "--failure-id",
                "composition_ratio_mismatch",
                "--issue",
                "README 样张为横向展示图。",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["$schema"], "output_evaluations.schema.json")
        self.assertEqual(payload["evaluations"][0]["character"], "furina")
        self.assertEqual(payload["evaluations"][0]["failure_ids"], ["composition_ratio_mismatch"])

        failures = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "new_output_evaluation.py"), "--list-failures"],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        self.assertIn("composition_ratio_mismatch", failures.stdout)

    def test_output_evaluation_cli_check_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "validate_output_evaluations.py"), "--check"],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        self.assertIn("OK：出图评分记录校验通过", result.stdout)

    def test_output_evaluation_summary_is_current(self) -> None:
        document = load_evaluation_json(ROOT / "评估" / "output_evaluations.example.json")
        report_path = ROOT / "评估" / "出图评分汇总.md"
        self.assertEqual(report_path.read_text(encoding="utf-8"), render_output_evaluation_summary(document, self.data))
        self.assertIn("composition_ratio_mismatch", report_path.read_text(encoding="utf-8"))

    def test_output_evaluation_summary_cli_check_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "summarize_output_evaluations.py"), "--check"],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        self.assertIn("OK：出图评分汇总已同步", result.stdout)

    def test_failure_fix_suggestions_are_current(self) -> None:
        document = load_evaluation_json(ROOT / "评估" / "output_evaluations.example.json")
        failure_lexicon = load_failure_fix_json(ROOT / "评估" / "failure_fix_lexicon.json")
        report_path = ROOT / "评估" / "失败修正建议.md"
        report = report_path.read_text(encoding="utf-8")
        self.assertEqual(report, render_fix_suggestions(document, self.data, failure_lexicon))
        self.assertIn("composition_ratio_mismatch", report)
        self.assertIn("请生成 9:16 竖图", report)

    def test_failure_fix_suggestions_cli_check_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "suggest_failure_fixes.py"), "--check"],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        self.assertIn("OK：失败修正建议已同步", result.stdout)

    def test_project_dashboard_is_current(self) -> None:
        report_path = ROOT / "评估" / "项目仪表盘.md"
        report = report_path.read_text(encoding="utf-8")
        self.assertEqual(report, render_project_dashboard())
        self.assertIn("项目仪表盘", report)
        self.assertIn("Prompt Packs", report)
        self.assertIn("标签覆盖矩阵", report)

    def test_project_dashboard_cli_check_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "build_project_dashboard.py"), "--check"],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        self.assertIn("OK：项目仪表盘已同步", result.stdout)

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
            width, height = image_dimensions(preview_dir / item["file"])
            self.assertEqual(item["width"], width)
            self.assertEqual(item["height"], height)
            self.assertEqual(item["aspect_ratio"], reduced_aspect_ratio(width, height))
            self.assertEqual(item["orientation"], classify_orientation(width, height))

    def test_preview_manifest_sync_tool_is_current(self) -> None:
        preview_dir = ROOT / "预览图"
        manifest_path = preview_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        synced = sync_manifest(manifest, preview_dir)
        self.assertEqual(render_preview_manifest(synced), manifest_path.read_text(encoding="utf-8"))

        result = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "sync_preview_manifest.py"), "--check"],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        self.assertIn("OK：预览图 manifest 尺寸元数据已同步", result.stdout)

    def test_gitignore_keeps_local_noise_out(self) -> None:
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for required in ["__pycache__/", "*.py[cod]", ".venv/", ".env", "原图/", "*.psd", ".DS_Store", "Thumbs.db"]:
            self.assertIn(required, gitignore)

    def test_secret_patterns_catch_realistic_tokens_not_placeholders(self) -> None:
        suspicious_samples = [
            "sk-" + "a" * 30,
            "github_pat_" + "A" * 30,
            "ghp_" + "B" * 30,
            "AKIA" + "C" * 16,
            "password=" + "d" * 30,
        ]
        for sample in suspicious_samples:
            with self.subTest(sample=sample[:8]):
                self.assertTrue(any(pattern.search(sample) for _label, pattern in SECRET_PATTERNS))

        placeholders = ["OPENAI_API_KEY", "api_key: <your-key>", "token: ${TOKEN}"]
        for sample in placeholders:
            with self.subTest(sample=sample):
                self.assertFalse(any(pattern.search(sample) for _label, pattern in SECRET_PATTERNS))


if __name__ == "__main__":
    unittest.main()
