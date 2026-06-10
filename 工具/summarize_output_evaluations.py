from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from build_prompt_pack import DEFAULT_CONFIG, load_config
from validate_output_evaluations import DEFAULT_EVALUATIONS, DEFAULT_FAILURE_FIX_LEXICON, SCORE_LIMITS, load_json, validate_document

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "评估" / "出图评分汇总.md"

SCORE_LABELS = {
    "role_consistency": "角色一致性",
    "composition_ratio": "构图与比例",
    "material_detail": "服装材质",
    "scene_match": "场景匹配",
    "public_safety": "安全与公开性",
    "text_ui": "文字与UI",
    "delivery_usefulness": "交付可用性",
}
DECISION_LABELS = {
    "keep": "保留",
    "edit": "编辑修正",
    "regenerate": "重新生成",
    "reject": "拒绝",
}


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def fmt_average(value: float) -> str:
    return f"{value:.1f}".rstrip("0").rstrip(".")


def table(headers: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return lines


def render_summary(document: dict[str, Any], config: dict[str, Any], failure_lexicon: dict[str, Any] | None = None) -> str:
    if failure_lexicon is None:
        failure_lexicon = load_json(DEFAULT_FAILURE_FIX_LEXICON)
    validation = validate_document(document, config, failure_lexicon=failure_lexicon)
    evaluations = document.get("evaluations", []) if isinstance(document.get("evaluations"), list) else []
    packs = {pack.get("id"): pack for pack in config.get("packs", []) if pack.get("id")}
    characters = config.get("characters", {})
    failure_titles = {
        str(rule.get("id", "")): str(rule.get("title", ""))
        for rule in failure_lexicon.get("rules", [])
        if isinstance(rule, dict) and rule.get("id")
    }

    total_scores = [int(item.get("total_score", 0)) for item in evaluations if isinstance(item, dict)]
    count = len(total_scores)
    average_total = sum(total_scores) / count if count else 0
    public_safe_count = sum(1 for item in evaluations if isinstance(item, dict) and item.get("public_safe") is True)
    decision_counts = Counter(str(item.get("decision", "")) for item in evaluations if isinstance(item, dict))

    lines = [
        "# 出图评分汇总",
        "",
        "这个报告由 `工具/summarize_output_evaluations.py` 自动生成，用于从结构化评分记录里快速查看平均分、决策分布和常见问题。",
        "",
        f"- 来源文件：`评估/output_evaluations.example.json`",
        f"- 记录数：{count}",
        f"- 平均总分：{fmt_average(average_total)} / 100",
        f"- 公开安全记录：{public_safe_count} / {count}",
        f"- 校验错误：{len(validation.errors)}",
        f"- 校验警告：{len(validation.warnings)}",
        "",
        "## 决策分布",
        "",
    ]
    decision_rows = []
    for decision in ["keep", "edit", "regenerate", "reject"]:
        decision_rows.append([DECISION_LABELS[decision], str(decision_counts.get(decision, 0))])
    lines.extend(table(["决策", "数量"], decision_rows))

    lines.extend(["", "## 分项平均分", ""])
    score_rows: list[list[str]] = []
    for key, max_value in SCORE_LIMITS.items():
        values = [
            int(item.get("scores", {}).get(key, 0))
            for item in evaluations
            if isinstance(item, dict) and isinstance(item.get("scores"), dict)
        ]
        average = sum(values) / len(values) if values else 0
        score_rows.append([SCORE_LABELS[key], f"{fmt_average(average)} / {max_value}"])
    lines.extend(table(["项目", "平均分"], score_rows))

    lines.extend(["", "## 常见问题", ""])
    issue_counter: Counter[str] = Counter()
    for item in evaluations:
        if not isinstance(item, dict):
            continue
        for issue in item.get("issues", []):
            if str(issue).strip():
                issue_counter[str(issue)] += 1
    if issue_counter:
        lines.extend(table(["问题", "次数"], [[issue, str(count)] for issue, count in issue_counter.most_common()]))
    else:
        lines.append("暂无。")

    lines.extend(["", "## 失败类型分布", ""])
    failure_counter: Counter[str] = Counter()
    for item in evaluations:
        if not isinstance(item, dict):
            continue
        for failure_id in item.get("failure_ids", []):
            if str(failure_id).strip():
                failure_counter[str(failure_id)] += 1
    if failure_counter:
        rows = [
            [failure_id, failure_titles.get(failure_id, "未知失败类型"), str(count)]
            for failure_id, count in failure_counter.most_common()
        ]
        lines.extend(table(["失败类型 ID", "名称", "次数"], rows))
    else:
        lines.append("暂无。")

    lines.extend(["", "## 记录明细", ""])
    detail_rows: list[list[str]] = []
    for item in evaluations:
        if not isinstance(item, dict):
            continue
        pack_id = str(item.get("prompt_pack", ""))
        char_id = str(item.get("character", ""))
        pack = packs.get(pack_id, {})
        character = characters.get(char_id, {})
        detail_rows.append(
            [
                str(item.get("id", "")),
                character.get("display_name", char_id),
                pack.get("title", pack_id),
                str(item.get("total_score", "")),
                DECISION_LABELS.get(str(item.get("decision", "")), str(item.get("decision", ""))),
                "、".join(str(failure_id) for failure_id in item.get("failure_ids", [])),
                str(item.get("next_action", "")),
            ]
        )
    lines.extend(table(["ID", "角色", "Prompt Pack", "总分", "决策", "失败类型", "下一步"], detail_rows))

    lines.extend(["", "## 校验结果", ""])
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
    parser = argparse.ArgumentParser(description="Summarize structured image output evaluation records.")
    parser.add_argument("--file", type=Path, default=DEFAULT_EVALUATIONS, help="Path to output evaluations JSON")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to prompt_packs.json")
    parser.add_argument("--failure-lexicon", type=Path, default=DEFAULT_FAILURE_FIX_LEXICON, help="Path to failure_fix_lexicon.json")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT, help="Path to generated Markdown summary")
    parser.add_argument("--check", action="store_true", help="Check whether the summary is current and valid")
    return parser.parse_args()


def main() -> int:
    configure_stdout()
    args = parse_args()
    document = load_json(args.file)
    config = load_config(args.config)
    failure_lexicon = load_json(args.failure_lexicon)
    validation = validate_document(document, config, failure_lexicon=failure_lexicon)
    report = render_summary(document, config, failure_lexicon)

    if args.check:
        if validation.errors:
            print("出图评分汇总校验失败：")
            for item in validation.errors:
                print(f"- {item}")
            return 1
        if not args.report.exists() or args.report.read_text(encoding="utf-8") != report:
            print("出图评分汇总已过期，请运行：python 工具/summarize_output_evaluations.py")
            return 1
        print("OK：出图评分汇总已同步。")
        return 0

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8", newline="\n")
    if validation.errors:
        print("出图评分汇总校验失败：")
        for item in validation.errors:
            print(f"- {item}")
        return 1
    print(f"已写入出图评分汇总：{args.report}")
    print("OK：出图评分汇总已同步。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
