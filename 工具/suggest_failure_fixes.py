from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from build_prompt_pack import DEFAULT_CONFIG, load_config
from validate_output_evaluations import DEFAULT_EVALUATIONS, DEFAULT_FAILURE_FIX_LEXICON, load_json, validate_document

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "评估" / "失败修正建议.md"

DECISION_LABELS = {
    "keep": "保留",
    "edit": "编辑修正",
    "regenerate": "重新生成",
    "reject": "拒绝",
}
ACTION_LABELS = {
    "edit": "编辑修正",
    "regenerate": "重新生成",
    "reject": "拒绝",
}


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def render_fix_suggestions(document: dict[str, Any], config: dict[str, Any], failure_lexicon: dict[str, Any]) -> str:
    validation = validate_document(document, config, failure_lexicon=failure_lexicon)
    evaluations = document.get("evaluations", []) if isinstance(document.get("evaluations"), list) else []
    packs = {pack.get("id"): pack for pack in config.get("packs", []) if pack.get("id")}
    characters = config.get("characters", {})
    failure_rules = {
        str(rule.get("id", "")): rule
        for rule in failure_lexicon.get("rules", [])
        if isinstance(rule, dict) and rule.get("id")
    }

    lines = [
        "# 失败修正建议",
        "",
        "这个报告由 `工具/suggest_failure_fixes.py` 根据结构化出图评分记录和失败修正词库自动生成。",
        "它把 `failure_ids` 转成可复制的修正提示词，方便决定编辑、重生成或拒绝。",
        "",
        f"- 来源评分：`评估/output_evaluations.example.json`",
        f"- 来源词库：`评估/failure_fix_lexicon.json`",
        f"- 记录数：{len(evaluations)}",
        f"- 校验错误：{len(validation.errors)}",
        f"- 校验警告：{len(validation.warnings)}",
        "",
    ]

    suggestion_count = 0
    for item in evaluations:
        if not isinstance(item, dict):
            continue
        failure_ids = [str(failure_id) for failure_id in item.get("failure_ids", []) if str(failure_id).strip()]
        if not failure_ids:
            continue
        suggestion_count += 1
        eval_id = str(item.get("id", ""))
        pack_id = str(item.get("prompt_pack", ""))
        char_id = str(item.get("character", ""))
        pack = packs.get(pack_id, {})
        character = characters.get(char_id, {})
        issues = [str(issue) for issue in item.get("issues", []) if str(issue).strip()]
        lines.extend(
            [
                f"## {suggestion_count}. {eval_id}",
                "",
                f"- 角色：{character.get('display_name', char_id)}",
                f"- Prompt Pack：{pack.get('title', pack_id)} (`{pack_id}`)",
                f"- 总分：{item.get('total_score', '')} / 100",
                f"- 当前决策：{DECISION_LABELS.get(str(item.get('decision', '')), str(item.get('decision', '')))}",
                f"- 记录里的下一步：{item.get('next_action', '')}",
                "",
                "### 问题记录",
                "",
            ]
        )
        if issues:
            lines.extend(f"- {issue}" for issue in issues)
        else:
            lines.append("暂无自由文本问题。")
        lines.extend(["", "### 建议修正", ""])
        for failure_id in failure_ids:
            rule = failure_rules.get(failure_id, {})
            title = str(rule.get("title", failure_id))
            action = str(rule.get("next_action", "edit"))
            lines.extend(
                [
                    f"#### `{failure_id}`：{title}",
                    "",
                    f"- 分类：`{rule.get('category', '')}`",
                    f"- 严重级别：`{rule.get('severity', '')}`",
                    f"- 建议动作：{ACTION_LABELS.get(action, action)}",
                    "",
                    "```text",
                    str(rule.get("fix_prompt", "")),
                    "```",
                    "",
                ]
            )

    if suggestion_count == 0:
        lines.extend(["## 建议", "", "当前评分记录没有填写 failure_ids，暂无自动修正建议。", ""])

    lines.extend(["## 校验结果", ""])
    if validation.errors:
        lines.extend(["### 错误", ""])
        lines.extend(f"- {item}" for item in validation.errors)
    else:
        lines.append("错误：无。")
    if validation.warnings:
        lines.extend(["", "### 警告", ""])
        lines.extend(f"- {item}" for item in validation.warnings)
    else:
        lines.append("警告：无。")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render actionable fix suggestions from output evaluations.")
    parser.add_argument("--file", type=Path, default=DEFAULT_EVALUATIONS, help="Path to output evaluations JSON")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to prompt_packs.json")
    parser.add_argument("--failure-lexicon", type=Path, default=DEFAULT_FAILURE_FIX_LEXICON, help="Path to failure_fix_lexicon.json")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT, help="Path to generated Markdown suggestions")
    parser.add_argument("--check", action="store_true", help="Check whether the suggestions report is current and valid")
    return parser.parse_args()


def main() -> int:
    configure_stdout()
    args = parse_args()
    document = load_json(args.file)
    config = load_config(args.config)
    failure_lexicon = load_json(args.failure_lexicon)
    validation = validate_document(document, config, failure_lexicon=failure_lexicon)
    report = render_fix_suggestions(document, config, failure_lexicon)

    if args.check:
        if validation.errors:
            print("失败修正建议校验失败：")
            for item in validation.errors:
                print(f"- {item}")
            return 1
        if not args.report.exists() or args.report.read_text(encoding="utf-8") != report:
            print("失败修正建议已过期，请运行：python 工具/suggest_failure_fixes.py")
            return 1
        print("OK：失败修正建议已同步。")
        return 0

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    if validation.errors:
        print("失败修正建议校验失败：")
        for item in validation.errors:
            print(f"- {item}")
        return 1
    print(f"已写入失败修正建议：{args.report}")
    print("OK：失败修正建议已同步。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
