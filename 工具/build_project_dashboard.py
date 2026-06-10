from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from build_prompt_pack import (
    DEFAULT_CONFIG,
    DEFAULT_TAG_TAXONOMY,
    GENERATED_API_REQUESTS_JSONL,
    GENERATED_CSV_INDEX,
    GENERATED_JSON_BUNDLE,
    GENERATED_TAG_COVERAGE_MATRIX,
    GENERATED_TAG_INDEX,
    config_digest,
    load_config,
    load_tag_taxonomy,
)
from validate_output_evaluations import DEFAULT_EVALUATIONS, DEFAULT_FAILURE_FIX_LEXICON, SCORE_LIMITS

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREVIEW_MANIFEST = ROOT / "预览图" / "manifest.json"
DEFAULT_REPORT = ROOT / "评估" / "项目仪表盘.md"


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} 根节点必须是 JSON object")
    return data


def table(headers: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return lines


def count_template_docs() -> int:
    template_dir = ROOT / "模板"
    return len([path for path in template_dir.glob("*.md") if path.name.lower() != "readme.md"])


def count_generated_markdown() -> int:
    generated_dir = ROOT / "生成提示词"
    return len(list(generated_dir.glob("*.md")))


def used_template_tags(config: dict[str, Any]) -> set[str]:
    return {
        str(tag)
        for template in config.get("templates", {}).values()
        if isinstance(template, dict)
        for tag in template.get("tags", [])
    }


def render_dashboard(
    config: dict[str, Any] | None = None,
    tag_taxonomy: dict[str, Any] | None = None,
    preview_manifest: dict[str, Any] | None = None,
    failure_lexicon: dict[str, Any] | None = None,
    evaluations: dict[str, Any] | None = None,
) -> str:
    config = config or load_config(DEFAULT_CONFIG)
    tag_taxonomy = tag_taxonomy or load_tag_taxonomy(DEFAULT_TAG_TAXONOMY)
    preview_manifest = preview_manifest or load_json(DEFAULT_PREVIEW_MANIFEST)
    failure_lexicon = failure_lexicon or load_json(DEFAULT_FAILURE_FIX_LEXICON)
    evaluations = evaluations or load_json(DEFAULT_EVALUATIONS)

    characters = config.get("characters", {})
    templates = config.get("templates", {})
    packs = config.get("packs", [])
    api_profiles = [
        template.get("api_profile", {})
        for template in templates.values()
        if isinstance(template, dict) and isinstance(template.get("api_profile"), dict)
    ]
    api_sizes = sorted({str(profile.get("size", "")) for profile in api_profiles if str(profile.get("size", "")).strip()})
    taxonomy_tags = tag_taxonomy.get("tags", []) if isinstance(tag_taxonomy.get("tags"), list) else []
    used_tags = used_template_tags(config)
    unused_tags = sorted(
        str(tag.get("id", ""))
        for tag in taxonomy_tags
        if isinstance(tag, dict) and str(tag.get("id", "")) not in used_tags
    )
    preview_images = preview_manifest.get("images", []) if isinstance(preview_manifest.get("images"), list) else []
    public_safe_previews = sum(1 for item in preview_images if isinstance(item, dict) and item.get("public_safe") is True)
    failure_rules = failure_lexicon.get("rules", []) if isinstance(failure_lexicon.get("rules"), list) else []
    evaluation_rows = evaluations.get("evaluations", []) if isinstance(evaluations.get("evaluations"), list) else []
    public_safe_evaluations = sum(1 for item in evaluation_rows if isinstance(item, dict) and item.get("public_safe") is True)
    total_scores = [int(item.get("total_score", 0)) for item in evaluation_rows if isinstance(item, dict)]
    average_score = round(sum(total_scores) / len(total_scores), 1) if total_scores else 0
    failure_counter: Counter[str] = Counter()
    for item in evaluation_rows:
        if not isinstance(item, dict):
            continue
        for failure_id in item.get("failure_ids", []):
            if str(failure_id).strip():
                failure_counter[str(failure_id)] += 1

    expected_pack_count = len(characters) * len(templates)
    coverage_text = f"{len(packs)} / {expected_pack_count}" if expected_pack_count else str(len(packs))

    lines = [
        "# 项目仪表盘",
        "",
        "这个文件由 `工具/build_project_dashboard.py` 自动生成，用来快速查看仓库当前覆盖、质量资产和评估资产。",
        "不要手工编辑；需要刷新时运行 `python 工具/run_quality_gate.py --refresh-generated`。",
        "",
        "## 总览",
        "",
    ]
    lines.extend(
        table(
            ["模块", "数量", "说明"],
            [
                ["角色", str(len(characters)), "芙宁娜、茜特菈莉、多莉 / 朵莉亚"],
                ["Prompt Pack 模板", str(len(templates)), "机器可组合输出类型"],
                ["API Profiles", f"{len(api_profiles)} / {len(templates)}", "`gpt-image-2` 推荐参数绑定"],
                ["Prompt Packs", coverage_text, "角色 × 输出类型覆盖"],
                ["模板文档", str(count_template_docs()), "`模板/` 下可人工复制的 Markdown 文件"],
                ["正式 tags", str(len(taxonomy_tags)), "`配置/tag_taxonomy.json` 中登记的标签"],
                ["已使用 tags", str(len(used_tags)), "`配置/prompt_packs.json` 当前实际使用的模板标签"],
                ["生成提示词 Markdown", str(count_generated_markdown()), "`生成提示词/` 下自动导出的 Markdown"],
                ["预览图", f"{public_safe_previews} / {len(preview_images)}", "public_safe / total"],
                ["失败修正规则", str(len(failure_rules)), "`评估/failure_fix_lexicon.json`"],
                ["结构化评分记录", str(len(evaluation_rows)), "`评估/output_evaluations.example.json`"],
            ],
        )
    )

    lines.extend(["", "## 覆盖健康", ""])
    if expected_pack_count and len(packs) == expected_pack_count:
        lines.append("- Prompt Pack 覆盖：完整。")
    else:
        lines.append("- Prompt Pack 覆盖：存在缺口，请查看 `生成提示词/覆盖矩阵.md`。")
    if templates and len(api_profiles) == len(templates):
        lines.append("- API 参数绑定：完整；当前尺寸档位：" + "、".join(f"`{size}`" for size in api_sizes) + "。")
    else:
        lines.append("- API 参数绑定：存在缺口，请检查 `配置/prompt_packs.json` 的 `templates.*.api_profile`。")
    if unused_tags:
        lines.append("- 未使用正式 tags：" + "、".join(f"`{tag}`" for tag in unused_tags))
    else:
        lines.append("- 未使用正式 tags：无。")
    if preview_images and public_safe_previews == len(preview_images):
        lines.append("- 预览图公开安全：全部 `public_safe=true`。")
    else:
        lines.append("- 预览图公开安全：存在未确认记录，请查看 `预览图/manifest.json`。")
    if evaluation_rows:
        lines.append(f"- 出图评分平均分：{average_score} / {sum(SCORE_LIMITS.values())}。")
    else:
        lines.append("- 出图评分平均分：暂无记录。")

    lines.extend(["", "## 失败类型快照", ""])
    if failure_counter:
        lines.extend(table(["failure_id", "次数"], [[failure_id, str(count)] for failure_id, count in failure_counter.most_common()]))
    else:
        lines.append("暂无失败类型记录。")

    lines.extend(
        [
            "",
            "## 快速入口",
            "",
            "- [`生成提示词/README.md`](../生成提示词/README.md)：按角色 × 用途复制 Prompt Pack。",
            "- [`生成提示词/覆盖矩阵.md`](../生成提示词/覆盖矩阵.md)：查看角色 × 输出类型覆盖。",
            f"- [`生成提示词/{GENERATED_TAG_INDEX}`](../生成提示词/{GENERATED_TAG_INDEX})：按 tag 查找 Prompt Pack。",
            f"- [`生成提示词/{GENERATED_TAG_COVERAGE_MATRIX}`](../生成提示词/{GENERATED_TAG_COVERAGE_MATRIX})：查看 tag 覆盖矩阵。",
            f"- [`生成提示词/{GENERATED_JSON_BUNDLE}`](../生成提示词/{GENERATED_JSON_BUNDLE})：机器可读 Prompt Pack JSON bundle。",
            f"- [`生成提示词/{GENERATED_API_REQUESTS_JSONL}`](../生成提示词/{GENERATED_API_REQUESTS_JSONL})：逐行 API 请求草稿 JSONL。",
            f"- [`生成提示词/{GENERATED_CSV_INDEX}`](../生成提示词/{GENERATED_CSV_INDEX})：表格索引。",
            "- [`评估/失败修正建议.md`](失败修正建议.md)：按评分记录生成可复制修正提示词。",
            "",
            "## 维护命令",
            "",
            "```powershell",
            "python 工具/run_quality_gate.py --refresh-generated",
            "python 工具/run_quality_gate.py",
            "```",
            "",
            f"- Prompt Pack 配置 SHA256：`{config_digest(config)}`",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build or check the generated project dashboard.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT, help="Path to generated dashboard Markdown")
    parser.add_argument("--check", action="store_true", help="Check whether the dashboard is current")
    return parser.parse_args()


def main() -> int:
    configure_stdout()
    args = parse_args()
    report = render_dashboard()
    report_path = args.report if args.report.is_absolute() else ROOT / args.report

    if args.check:
        if not report_path.exists() or report_path.read_text(encoding="utf-8") != report:
            print("项目仪表盘已过期，请运行：python 工具/build_project_dashboard.py")
            return 1
        print("OK：项目仪表盘已同步。")
        return 0

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(f"已写入项目仪表盘：{report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
