from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

from build_prompt_pack import DEFAULT_CONFIG, get_pack, load_config
from validate_output_evaluations import DEFAULT_FAILURE_FIX_LEXICON, SCORE_LIMITS, load_json

ROOT = Path(__file__).resolve().parents[1]

ID_RE = re.compile(r"[^a-z0-9_-]+")


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def slugify(value: str, fallback: str = "evaluation") -> str:
    slug = ID_RE.sub("-", value.lower()).strip("-_")
    if not slug or not re.match(r"^[a-z0-9]", slug):
        return fallback
    return slug


def default_record_id(prompt_pack: str, image_file: str) -> str:
    stem = Path(image_file).stem
    return slugify(f"{prompt_pack}-{stem}")


def parse_score_assignment(raw: str) -> tuple[str, int]:
    if "=" not in raw:
        raise ValueError(f"--score 必须写成 key=value：{raw}")
    key, value_text = raw.split("=", 1)
    key = key.strip()
    if key not in SCORE_LIMITS:
        raise ValueError(f"未知评分项：{key}。可用：{', '.join(SCORE_LIMITS)}")
    try:
        value = int(value_text)
    except ValueError as exc:
        raise ValueError(f"评分必须是整数：{raw}") from exc
    max_value = SCORE_LIMITS[key]
    if value < 0 or value > max_value:
        raise ValueError(f"{key} 必须在 0-{max_value}：{value}")
    return key, value


def parse_scores(assignments: list[str] | None) -> dict[str, int]:
    scores = {key: 0 for key in SCORE_LIMITS}
    for raw in assignments or []:
        key, value = parse_score_assignment(raw)
        scores[key] = value
    return scores


def failure_rule_lookup(failure_lexicon: dict[str, Any]) -> dict[str, str]:
    return {
        str(rule.get("id", "")): str(rule.get("title", ""))
        for rule in failure_lexicon.get("rules", [])
        if isinstance(rule, dict) and rule.get("id")
    }


def validate_failure_ids(failure_ids: list[str], failure_lexicon: dict[str, Any]) -> None:
    known = failure_rule_lookup(failure_lexicon)
    duplicates = sorted({failure_id for failure_id in failure_ids if failure_ids.count(failure_id) > 1})
    if duplicates:
        raise ValueError(f"failure_ids 重复：{', '.join(duplicates)}")
    unknown = [failure_id for failure_id in failure_ids if failure_id not in known]
    if unknown:
        raise ValueError(f"failure_ids 未登记：{', '.join(unknown)}。可用：{', '.join(sorted(known))}")


def build_record(
    config: dict[str, Any],
    prompt_pack: str,
    image_file: str,
    *,
    record_id: str | None = None,
    record_date: str | None = None,
    scores: dict[str, int] | None = None,
    public_safe: bool = False,
    decision: str = "regenerate",
    failure_ids: list[str] | None = None,
    issues: list[str] | None = None,
    next_action: str = "待评估：填写具体问题、失败类型和下一步操作。",
    notes: str = "由 工具/new_output_evaluation.py 生成的出图评分骨架。",
) -> dict[str, Any]:
    pack = get_pack(config, prompt_pack)
    score_values = {key: 0 for key in SCORE_LIMITS}
    if scores:
        score_values.update(scores)
    total_score = sum(score_values.values())

    return {
        "id": record_id or default_record_id(prompt_pack, image_file),
        "date": record_date or date.today().isoformat(),
        "prompt_pack": prompt_pack,
        "character": pack["character"],
        "image_file": image_file,
        "scores": score_values,
        "total_score": total_score,
        "public_safe": public_safe,
        "decision": decision,
        "failure_ids": failure_ids or [],
        "issues": issues or [],
        "next_action": next_action,
        "notes": notes,
    }


def build_document(records: list[dict[str, Any]], *, version: str | None = None, description: str | None = None) -> dict[str, Any]:
    today = date.today().isoformat()
    return {
        "$schema": "output_evaluations.schema.json",
        "version": version or f"{today}-output-evaluations-draft",
        "description": description or "由 工具/new_output_evaluation.py 生成的结构化出图评分记录草稿。",
        "evaluations": records,
    }


def to_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def list_failures(failure_lexicon: dict[str, Any]) -> str:
    rows = ["可用 failure_ids："]
    for failure_id, title in sorted(failure_rule_lookup(failure_lexicon).items()):
        rows.append(f"- {failure_id}：{title}")
    return "\n".join(rows) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a skeleton output evaluation JSON record from a Prompt Pack and image path.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to prompt_packs.json")
    parser.add_argument("--failure-lexicon", type=Path, default=DEFAULT_FAILURE_FIX_LEXICON, help="Path to failure_fix_lexicon.json")
    parser.add_argument("--list-failures", action="store_true", help="List available failure_ids and exit")
    parser.add_argument("--prompt-pack", help="Prompt Pack id, for example furina_readme_preview")
    parser.add_argument("--image-file", help="Image path relative to repository root, for example 预览图/furina-dessert-01.jpg")
    parser.add_argument("--id", help="Evaluation record id. Defaults to prompt-pack plus image stem.")
    parser.add_argument("--date", help="Evaluation date in YYYY-MM-DD. Defaults to today.")
    parser.add_argument("--score", action="append", help="Score override such as role_consistency=23. Can be used multiple times.")
    parser.add_argument("--public-safe", action=argparse.BooleanOptionalAction, default=False, help="Set public_safe. Defaults to false.")
    parser.add_argument("--decision", choices=["keep", "edit", "regenerate", "reject"], default="regenerate")
    parser.add_argument("--failure-id", action="append", default=[], help="Failure id from failure_fix_lexicon.json. Can be used multiple times.")
    parser.add_argument("--issue", action="append", default=[], help="Issue text. Can be used multiple times.")
    parser.add_argument("--next-action", default="待评估：填写具体问题、失败类型和下一步操作。")
    parser.add_argument("--notes", default="由 工具/new_output_evaluation.py 生成的出图评分骨架。")
    parser.add_argument("--record-only", action="store_true", help="Output only the evaluation record instead of a full document.")
    parser.add_argument("--out", type=Path, help="Write JSON to this path instead of stdout.")
    return parser.parse_args()


def main() -> int:
    configure_stdout()
    args = parse_args()
    failure_lexicon = load_json(args.failure_lexicon)

    if args.list_failures:
        print(list_failures(failure_lexicon), end="")
        return 0

    if not args.prompt_pack or not args.image_file:
        print("必须提供 --prompt-pack 和 --image-file，或使用 --list-failures。", file=sys.stderr)
        return 2

    try:
        config = load_config(args.config)
        scores = parse_scores(args.score)
        validate_failure_ids(args.failure_id, failure_lexicon)
        record = build_record(
            config,
            args.prompt_pack,
            args.image_file,
            record_id=args.id,
            record_date=args.date,
            scores=scores,
            public_safe=args.public_safe,
            decision=args.decision,
            failure_ids=args.failure_id,
            issues=args.issue,
            next_action=args.next_action,
            notes=args.notes,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"生成出图评分骨架失败：{exc}", file=sys.stderr)
        return 1

    payload = record if args.record_only else build_document([record])
    output = to_json(payload)

    if args.out:
        out_path = args.out if args.out.is_absolute() else ROOT / args.out
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8", newline="\n")
        print(f"已写入出图评分骨架：{out_path}")
        return 0

    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
