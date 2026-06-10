from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from build_prompt_pack import DEFAULT_CONFIG, load_config

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEXICON = ROOT / "评估" / "failure_fix_lexicon.json"
DEFAULT_SCHEMA = ROOT / "评估" / "failure_fix_lexicon.schema.json"
DEFAULT_MARKDOWN = ROOT / "评估" / "失败修正词库.md"

CATEGORIES = {
    "character_consistency",
    "role_anchor",
    "costume_material",
    "consistency_layout",
    "safety",
    "text_rendering",
    "anatomy_props",
    "scene_composition",
    "photography_style",
    "composition",
}
SEVERITIES = {"low", "medium", "high", "critical"}
NEXT_ACTIONS = {"edit", "regenerate", "reject"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_]*$")
APPLIES_TO_RE = re.compile(r"^(all|[a-z0-9][a-z0-9_]*)$")
NON_BLANK_PATTERN = "\\S"
TOP_LEVEL_FIELDS = {"$schema", "version", "description", "rules"}
RULE_FIELDS = {
    "id",
    "title",
    "category",
    "severity",
    "applies_to",
    "detect_terms",
    "problem",
    "fix_prompt",
    "must_include",
    "next_action",
}


@dataclass(frozen=True)
class FailureFixLexiconResult:
    errors: list[str]
    warnings: list[str]
    rows: list[list[str]]


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} 根节点必须是 JSON object")
    return data


def validate_schema_file(schema_path: Path = DEFAULT_SCHEMA) -> list[str]:
    errors: list[str] = []
    if not schema_path.exists():
        return [f"缺少失败修正词库 schema：{schema_path}"]
    try:
        schema = load_json(schema_path)
    except Exception as exc:  # noqa: BLE001
        return [f"失败修正词库 schema 无法读取：{exc}"]
    for key in ["$schema", "$id", "title", "type", "required", "properties", "$defs"]:
        if key not in schema:
            errors.append(f"失败修正词库 schema 缺少字段：{key}")
    if schema.get("additionalProperties") is not False:
        errors.append("失败修正词库 schema 根节点应设置 additionalProperties=false")
    for key in ["$schema", "version", "description", "rules"]:
        if key not in schema.get("properties", {}):
            errors.append(f"失败修正词库 schema.properties 缺少：{key}")
    for key in ["version", "description"]:
        prop = schema.get("properties", {}).get(key, {})
        if prop.get("minLength") != 1 or prop.get("pattern") != NON_BLANK_PATTERN:
            errors.append(f"失败修正词库 schema.properties.{key} 应设置 minLength=1 且 pattern=\\S")
    rule_schema = schema.get("$defs", {}).get("rule", {})
    if rule_schema.get("additionalProperties") is not False:
        errors.append("失败修正词库 schema.rule 应设置 additionalProperties=false")
    rule_props = rule_schema.get("properties", {})
    for key in ["id", "title", "category", "severity", "fix_prompt", "must_include", "next_action"]:
        if key not in rule_props:
            errors.append(f"失败修正词库 schema.rule.properties 缺少：{key}")
    if rule_props.get("id", {}).get("pattern") != ID_RE.pattern:
        errors.append("失败修正词库 schema.rule.properties.id 应限制为小写 slug")
    for key in ["title", "problem", "fix_prompt"]:
        prop = rule_props.get(key, {})
        if prop.get("minLength") != 1 or prop.get("pattern") != NON_BLANK_PATTERN:
            errors.append(f"失败修正词库 schema.rule.properties.{key} 应设置 minLength=1 且 pattern=\\S")
    applies_items = rule_props.get("applies_to", {}).get("items", {})
    if rule_props.get("applies_to", {}).get("uniqueItems") is not True or applies_items.get("pattern") != APPLIES_TO_RE.pattern:
        errors.append("失败修正词库 schema.rule.properties.applies_to 应设置 uniqueItems=true 且限制为 all 或角色 slug")
    for key in ["detect_terms", "must_include"]:
        prop = rule_props.get(key, {})
        items = prop.get("items", {})
        if prop.get("uniqueItems") is not True or items.get("minLength") != 1 or items.get("pattern") != NON_BLANK_PATTERN:
            errors.append(f"失败修正词库 schema.rule.properties.{key} 应设置 uniqueItems=true 且 items 非空白")
    return errors


def validate_document(document: dict[str, Any], config: dict[str, Any]) -> FailureFixLexiconResult:
    errors = validate_schema_file()
    warnings: list[str] = []
    rows: list[list[str]] = []

    if document.get("$schema") != "failure_fix_lexicon.schema.json":
        errors.append("失败修正词库 $schema 必须是 failure_fix_lexicon.schema.json")
    top_level_extra = sorted(set(document) - TOP_LEVEL_FIELDS)
    if top_level_extra:
        errors.append(f"失败修正词库存在未知顶层字段：{', '.join(top_level_extra)}")
    for key in ["version", "description"]:
        value = document.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"失败修正词库缺少 {key}")

    rules = document.get("rules")
    if not isinstance(rules, list) or not rules:
        errors.append("失败修正词库 rules 必须是非空 array")
        return FailureFixLexiconResult(errors, warnings, rows)

    character_ids = set(config.get("characters", {}))
    seen_ids: set[str] = set()

    for index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            errors.append(f"rules[{index}] 必须是 object")
            continue

        rule_id = str(rule.get("id", ""))
        context = rule_id or f"rules[{index}]"
        extra_fields = sorted(set(rule) - RULE_FIELDS)
        if extra_fields:
            errors.append(f"{context} 存在未知字段：{', '.join(extra_fields)}")
        title = str(rule.get("title", ""))
        category = str(rule.get("category", ""))
        severity = str(rule.get("severity", ""))
        next_action = str(rule.get("next_action", ""))
        fix_prompt = str(rule.get("fix_prompt", ""))
        problem = str(rule.get("problem", ""))

        if not ID_RE.match(rule_id):
            errors.append(f"rules[{index}] id 格式错误：{rule_id}")
        if rule_id in seen_ids:
            errors.append(f"失败修正词库 id 重复：{rule_id}")
        seen_ids.add(rule_id)
        if not title.strip():
            errors.append(f"{rule_id} 缺少 title")
        if category not in CATEGORIES:
            errors.append(f"{rule_id} category 必须是已知分类：{category}")
        if severity not in SEVERITIES:
            errors.append(f"{rule_id} severity 必须是 {', '.join(sorted(SEVERITIES))} 之一")
        if next_action not in NEXT_ACTIONS:
            errors.append(f"{rule_id} next_action 必须是 {', '.join(sorted(NEXT_ACTIONS))} 之一")
        if not problem.strip():
            errors.append(f"{rule_id} 缺少 problem")
        if len(fix_prompt.strip()) < 20:
            errors.append(f"{rule_id} fix_prompt 过短，无法作为可复制修正词")

        applies_to = rule.get("applies_to")
        if not isinstance(applies_to, list) or not applies_to:
            errors.append(f"{rule_id} applies_to 必须是非空 array")
            applies_values: list[str] = []
        else:
            applies_values = []
            for value in applies_to:
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"{rule_id} applies_to 不能包含空值")
                    continue
                if not APPLIES_TO_RE.match(value):
                    errors.append(f"{rule_id} applies_to 必须是 all 或角色 slug：{value}")
                    continue
                applies_values.append(value)
            applies_set = set(applies_values)
            duplicate_applies = sorted({value for value in applies_values if applies_values.count(value) > 1})
            if duplicate_applies:
                errors.append(f"{rule_id} applies_to 存在重复值：{', '.join(duplicate_applies)}")
            if "all" in applies_set and len(applies_set) > 1:
                errors.append(f"{rule_id} applies_to 不能同时包含 all 和具体角色")
            unknown_characters = sorted(applies_set - character_ids - {"all"})
            if unknown_characters:
                errors.append(f"{rule_id} applies_to 引用不存在的角色：{', '.join(unknown_characters)}")

        for field in ["detect_terms", "must_include"]:
            values = rule.get(field)
            if not isinstance(values, list) or not values:
                errors.append(f"{rule_id} {field} 必须是非空 array")
                continue
            cleaned_values: list[str] = []
            for value in values:
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"{rule_id} {field} 不能包含空值")
                    continue
                cleaned_values.append(value)
            duplicates = sorted({value for value in cleaned_values if cleaned_values.count(value) > 1})
            if duplicates:
                errors.append(f"{rule_id} {field} 存在重复值：{', '.join(duplicates)}")

        must_include = rule.get("must_include")
        if isinstance(must_include, list):
            for term in must_include:
                if isinstance(term, str) and term and term not in fix_prompt:
                    errors.append(f"{rule_id} fix_prompt 缺少 must_include 词：{term}")

        if category == "safety":
            for term in ["非低俗", "不性感化"]:
                if term not in fix_prompt:
                    errors.append(f"{rule_id} 安全修正词缺少：{term}")
            if severity != "critical":
                warnings.append(f"{rule_id} 是安全类规则，建议 severity=critical")

        if rule_id == "furina_contamination":
            for term in ["芙宁娜", "白蓝短发", "蓝黑礼帽", "枫丹蓝白歌剧服"]:
                if term not in fix_prompt:
                    errors.append(f"{rule_id} 芙宁娜污染修正词缺少：{term}")
            if set(rule.get("applies_to", [])) & {"furina"}:
                errors.append("furina_contamination 不应应用到 furina 自身")

        rows.append([rule_id, title, category, severity, next_action])

    expected_core_rules = {
        "furina_contamination",
        "wrong_hair_color",
        "ordinary_clothing",
        "multi_panel_drift",
        "public_safety_lowbrow",
        "garbled_text",
        "hands_props_error",
        "busy_background",
        "too_staged",
        "bad_crop",
    }
    missing_core = sorted(expected_core_rules - seen_ids)
    if missing_core:
        errors.append("失败修正词库缺少核心规则：" + "、".join(missing_core))

    return FailureFixLexiconResult(errors, warnings, rows)


def render_markdown(document: dict[str, Any]) -> str:
    lines = [
        "# 失败修正词库",
        "",
        "这个文件由 `工具/validate_failure_fix_lexicon.py` 根据 `评估/failure_fix_lexicon.json` 生成。",
        "这里记录常见失败类型、识别线索和对应修正写法。",
        "适合 gpt-image-2 的写法是自然语言约束，不是单纯堆 negative prompt。",
        "",
        f"- 规则版本：`{document.get('version', '')}`",
        f"- 规则数量：{len(document.get('rules', [])) if isinstance(document.get('rules'), list) else 0}",
        "",
        "## 使用方式",
        "",
        "1. 先在出图评分里记录具体问题。",
        "2. 到本文件找到对应失败类型。",
        "3. 复制“修正”里的自然语言约束做编辑或重生成。",
        "4. 如果要新增失败类型，修改 `评估/failure_fix_lexicon.json`，再运行：",
        "",
        "```powershell",
        "python 工具/validate_failure_fix_lexicon.py",
        "```",
        "",
    ]
    for number, rule in enumerate(document.get("rules", []), start=1):
        applies_to = "、".join(str(item) for item in rule.get("applies_to", []))
        detect_terms = "、".join(str(item) for item in rule.get("detect_terms", []))
        lines.extend(
            [
                f"## {number}. {rule.get('title', '')}",
                "",
                f"- ID：`{rule.get('id', '')}`",
                f"- 分类：`{rule.get('category', '')}`",
                f"- 严重级别：`{rule.get('severity', '')}`",
                f"- 适用角色：{applies_to}",
                f"- 后续动作：`{rule.get('next_action', '')}`",
                f"- 识别线索：{detect_terms}",
                "",
                "问题：",
                "",
                "```text",
                str(rule.get("problem", "")),
                "```",
                "",
                "修正：",
                "",
                "```text",
                str(rule.get("fix_prompt", "")),
                "```",
                "",
            ]
        )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate and render the structured failure-fix lexicon.")
    parser.add_argument("--file", type=Path, default=DEFAULT_LEXICON, help="Path to failure_fix_lexicon.json")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to prompt_packs.json")
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN, help="Path to rendered Markdown lexicon")
    parser.add_argument("--check", action="store_true", help="Validate JSON and check whether Markdown is current")
    return parser.parse_args()


def main() -> int:
    configure_stdout()
    args = parse_args()
    document = load_json(args.file)
    config = load_config(args.config)
    result = validate_document(document, config)
    rendered = render_markdown(document)

    print("# 失败修正词库校验")
    print(f"文件：{args.file}")
    print(f"规则数：{len(document.get('rules', [])) if isinstance(document.get('rules'), list) else 0}")
    print(f"错误：{len(result.errors)}")
    print(f"警告：{len(result.warnings)}")
    if result.errors:
        print("\n## 错误")
        for item in result.errors:
            print(f"- {item}")
    if result.warnings:
        print("\n## 警告")
        for item in result.warnings:
            print(f"- {item}")
    if result.errors:
        return 1

    if args.check:
        if not args.markdown.exists() or args.markdown.read_text(encoding="utf-8") != rendered:
            print(f"\n失败修正词库 Markdown 已过期，请运行：python 工具/validate_failure_fix_lexicon.py")
            return 1
        print("\nOK：失败修正词库校验通过，Markdown 已同步。")
        return 0

    args.markdown.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"\n已写入失败修正词库 Markdown：{args.markdown}")
    print("OK：失败修正词库校验通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
