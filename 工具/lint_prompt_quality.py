from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from build_prompt_pack import DEFAULT_CONFIG, load_config, render_pack

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES = ROOT / "评估" / "prompt_quality_rules.json"
DEFAULT_REPORT = ROOT / "评估" / "Prompt文本质量审计报告.md"


@dataclass(frozen=True)
class PromptQualityResult:
    errors: list[str]
    warnings: list[str]
    rows: list[list[str]]


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def mark(ok: bool) -> str:
    return "OK" if ok else "FAIL"


def missing_terms(text: str, terms: list[str]) -> list[str]:
    return [term for term in terms if term not in text]


def load_rules(path: Path = DEFAULT_RULES) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Prompt 质量规则根节点必须是 JSON object")
    return data


def validate_rules(rules: dict[str, Any], data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in [
        "$schema",
        "version",
        "description",
        "length",
        "required_sections",
        "required_safety_terms",
        "required_quality_terms",
        "forbidden_terms",
        "template_terms",
    ]:
        if key not in rules:
            errors.append(f"Prompt 质量规则缺少字段：{key}")
    length = rules.get("length", {})
    if not isinstance(length, dict):
        errors.append("Prompt 质量规则 length 必须是 object")
    else:
        min_chars = length.get("min_chars")
        max_chars = length.get("max_chars")
        if not isinstance(min_chars, int) or min_chars <= 0:
            errors.append("Prompt 质量规则 length.min_chars 必须是正整数")
        if not isinstance(max_chars, int) or max_chars <= 0:
            errors.append("Prompt 质量规则 length.max_chars 必须是正整数")
        if isinstance(min_chars, int) and isinstance(max_chars, int) and min_chars >= max_chars:
            errors.append("Prompt 质量规则 length.min_chars 必须小于 max_chars")

    for key in ["required_sections", "required_safety_terms", "required_quality_terms", "forbidden_terms"]:
        if not isinstance(rules.get(key), list) or not rules.get(key):
            errors.append(f"Prompt 质量规则 {key} 必须是非空 array")

    template_terms = rules.get("template_terms")
    templates = data.get("templates", {})
    if not isinstance(template_terms, dict) or not template_terms:
        errors.append("Prompt 质量规则 template_terms 必须是非空 object")
    else:
        missing_templates = sorted(set(templates) - set(template_terms))
        extra_templates = sorted(set(template_terms) - set(templates))
        if missing_templates:
            errors.append("Prompt 质量规则缺少模板覆盖：" + "、".join(missing_templates))
        if extra_templates:
            errors.append("Prompt 质量规则包含不存在的模板：" + "、".join(extra_templates))
        for template_id, terms in template_terms.items():
            if not isinstance(terms, list) or not terms:
                errors.append(f"Prompt 质量规则 template_terms.{template_id} 必须是非空 array")

    schema_ref = rules.get("$schema")
    if schema_ref:
        schema_path = (DEFAULT_RULES.parent / str(schema_ref)).resolve()
        try:
            schema_path.relative_to(DEFAULT_RULES.parent.resolve())
        except ValueError:
            errors.append(f"Prompt 质量规则 $schema 不能指向评估目录之外：{schema_ref}")
        if not schema_path.exists():
            errors.append(f"Prompt 质量规则 schema 文件不存在：评估/{schema_ref}")
    return errors


def lint(data: dict[str, Any], rules: dict[str, Any]) -> PromptQualityResult:
    errors = validate_rules(rules, data)
    warnings: list[str] = []
    rows: list[list[str]] = []
    if errors:
        return PromptQualityResult(errors, warnings, rows)

    min_chars = int(rules["length"]["min_chars"])
    max_chars = int(rules["length"]["max_chars"])
    characters = data.get("characters", {})
    templates = data.get("templates", {})

    for pack in data.get("packs", []):
        pack_id = str(pack.get("id", ""))
        char_id = str(pack.get("character", ""))
        template_id = str(pack.get("template", ""))
        prompt = render_pack(data, pack_id)
        prompt_len = len(prompt)

        missing_section_terms = missing_terms(prompt, [str(item) for item in rules["required_sections"]])
        missing_safety_terms = missing_terms(prompt, [str(item) for item in rules["required_safety_terms"]])
        missing_quality_terms = missing_terms(prompt, [str(item) for item in rules["required_quality_terms"]])
        prompt_folded = prompt.casefold()
        found_forbidden_terms = [
            str(item)
            for item in rules["forbidden_terms"]
            if str(item) and str(item).casefold() in prompt_folded
        ]
        missing_template_terms = missing_terms(prompt, [str(item) for item in rules["template_terms"].get(template_id, [])])
        missing_role_terms = missing_terms(prompt, [str(item) for item in characters[char_id].get("must_keep", [])])
        length_ok = min_chars <= prompt_len <= max_chars

        if missing_section_terms:
            errors.append(f"{pack_id} 缺少结构段落：{', '.join(missing_section_terms)}")
        if missing_safety_terms:
            errors.append(f"{pack_id} 缺少安全/防串词：{', '.join(missing_safety_terms)}")
        if missing_quality_terms:
            errors.append(f"{pack_id} 缺少质量词：{', '.join(missing_quality_terms)}")
        if found_forbidden_terms:
            errors.append(f"{pack_id} 含禁用词/平台参数：{', '.join(found_forbidden_terms)}")
        if missing_template_terms:
            errors.append(f"{pack_id} 缺少模板意图词：{', '.join(missing_template_terms)}")
        if missing_role_terms:
            errors.append(f"{pack_id} 缺少角色识别点：{', '.join(missing_role_terms)}")
        if not length_ok:
            errors.append(f"{pack_id} 长度 {prompt_len} 不在范围 {min_chars}-{max_chars}")

        rows.append(
            [
                pack_id,
                characters[char_id].get("display_name", char_id),
                templates[template_id].get("task_type", template_id),
                str(prompt_len),
                mark(not missing_section_terms),
                mark(not missing_safety_terms),
                mark(not missing_quality_terms),
                mark(not found_forbidden_terms),
                mark(not missing_template_terms),
                mark(not missing_role_terms),
                mark(length_ok),
            ]
        )

    return PromptQualityResult(errors, warnings, rows)


def table(headers: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return lines


def render_report(data: dict[str, Any], rules: dict[str, Any]) -> str:
    result = lint(data, rules)
    lines = [
        "# Prompt 文本质量审计报告",
        "",
        "这个报告由 `工具/lint_prompt_quality.py` 自动生成，用于在出图前检查 Prompt Pack 文本是否保留结构、安全、防串、模板意图和角色识别点，并避免混入 Midjourney / Stable Diffusion 等平台参数。",
        "",
        f"- 规则版本：`{rules.get('version', '')}`",
        f"- Prompt Pack 数量：{len(data.get('packs', []))}",
        f"- 错误：{len(result.errors)}",
        f"- 警告：{len(result.warnings)}",
        "",
        "## 检查矩阵",
        "",
    ]
    lines.extend(
        table(
            ["Prompt Pack", "角色", "模板", "长度", "结构", "安全", "质量", "禁用词", "模板词", "角色词", "长度范围"],
            result.rows,
        )
    )
    lines.extend(["", "## 错误", ""])
    if result.errors:
        lines.extend(f"- {item}" for item in result.errors)
    else:
        lines.append("无。")
    lines.extend(["", "## 警告", ""])
    if result.warnings:
        lines.extend(f"- {item}" for item in result.warnings)
    else:
        lines.append("无。")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lint rendered Prompt Pack text before image generation.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to prompt_packs.json")
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES, help="Path to prompt quality rules JSON")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT, help="Path to generated Markdown report")
    parser.add_argument("--check", action="store_true", help="Check whether the report is current and rules pass")
    return parser.parse_args()


def main() -> int:
    configure_stdout()
    args = parse_args()
    data = load_config(args.config)
    rules = load_rules(args.rules)
    result = lint(data, rules)
    report = render_report(data, rules)

    if args.check:
        if result.errors:
            print("Prompt 文本质量审计失败：")
            for item in result.errors:
                print(f"- {item}")
            return 1
        if not args.report.exists() or args.report.read_text(encoding="utf-8") != report:
            print(f"Prompt 文本质量审计报告已过期，请运行：python 工具/lint_prompt_quality.py")
            return 1
        print("OK：Prompt 文本质量审计通过。")
        return 0

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    if result.errors:
        print("Prompt 文本质量审计失败：")
        for item in result.errors:
            print(f"- {item}")
        return 1
    print(f"已写入 Prompt 文本质量审计报告：{args.report}")
    print("OK：Prompt 文本质量审计通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
