from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import date as date_type
from pathlib import Path
from typing import Any

from build_prompt_pack import DEFAULT_CONFIG, load_config

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVALUATIONS = ROOT / "评估" / "output_evaluations.example.json"
DEFAULT_SCHEMA = ROOT / "评估" / "output_evaluations.schema.json"
DEFAULT_FAILURE_FIX_LEXICON = ROOT / "评估" / "failure_fix_lexicon.json"

SCORE_LIMITS = {
    "role_consistency": 25,
    "composition_ratio": 15,
    "material_detail": 15,
    "scene_match": 10,
    "public_safety": 15,
    "text_ui": 10,
    "delivery_usefulness": 10,
}
DECISIONS = {"keep", "edit", "regenerate", "reject"}
DATE_RE = re.compile(r"^20[0-9]{2}-[0-9]{2}-[0-9]{2}$")
IMAGE_FILE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


@dataclass(frozen=True)
class EvaluationValidationResult:
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
        return [f"缺少出图评分 schema：{schema_path}"]
    try:
        schema = load_json(schema_path)
    except Exception as exc:  # noqa: BLE001
        return [f"出图评分 schema 无法读取：{exc}"]
    for key in ["$schema", "$id", "title", "type", "required", "properties", "$defs"]:
        if key not in schema:
            errors.append(f"出图评分 schema 缺少字段：{key}")
    for key in ["$schema", "version", "description", "evaluations"]:
        if key not in schema.get("properties", {}):
            errors.append(f"出图评分 schema.properties 缺少：{key}")
    evaluation_props = schema.get("$defs", {}).get("evaluation", {}).get("properties", {})
    for key in ["prompt_pack", "character", "scores", "total_score", "decision", "failure_ids"]:
        if key not in evaluation_props:
            errors.append(f"出图评分 schema.evaluation.properties 缺少：{key}")
    image_pattern = evaluation_props.get("image_file", {}).get("pattern", "")
    if "jpg" not in image_pattern or "webp" not in image_pattern:
        errors.append("出图评分 schema.evaluation.properties.image_file 应限制为图片文件后缀")
    if evaluation_props.get("failure_ids", {}).get("uniqueItems") is not True:
        errors.append("出图评分 schema.evaluation.properties.failure_ids 应设置 uniqueItems=true")
    return errors


def validate_document(
    document: dict[str, Any],
    config: dict[str, Any],
    root: Path = ROOT,
    failure_lexicon: dict[str, Any] | None = None,
) -> EvaluationValidationResult:
    errors = validate_schema_file()
    warnings: list[str] = []
    rows: list[list[str]] = []
    if failure_lexicon is None:
        failure_lexicon = load_json(DEFAULT_FAILURE_FIX_LEXICON)
    failure_rule_ids = {
        str(rule.get("id", ""))
        for rule in failure_lexicon.get("rules", [])
        if isinstance(rule, dict) and rule.get("id")
    }

    if document.get("$schema") != "output_evaluations.schema.json":
        errors.append("出图评分记录 $schema 必须是 output_evaluations.schema.json")

    evaluations = document.get("evaluations")
    if not isinstance(evaluations, list) or not evaluations:
        errors.append("出图评分记录 evaluations 必须是非空 array")
        return EvaluationValidationResult(errors, warnings, rows)

    packs = {pack.get("id"): pack for pack in config.get("packs", []) if pack.get("id")}
    characters = config.get("characters", {})
    seen_ids: set[str] = set()

    for index, item in enumerate(evaluations):
        if not isinstance(item, dict):
            errors.append(f"evaluations[{index}] 必须是 object")
            continue
        eval_id = str(item.get("id", ""))
        if not eval_id:
            errors.append(f"evaluations[{index}] 缺少 id")
        if eval_id in seen_ids:
            errors.append(f"出图评分 id 重复：{eval_id}")
        seen_ids.add(eval_id)

        date_text = str(item.get("date", ""))
        if not DATE_RE.match(date_text):
            errors.append(f"{eval_id} date 必须是 YYYY-MM-DD：{date_text}")
        else:
            try:
                date_type.fromisoformat(date_text)
            except ValueError:
                errors.append(f"{eval_id} date 不是有效日期：{date_text}")

        prompt_pack = str(item.get("prompt_pack", ""))
        pack = packs.get(prompt_pack)
        if not pack:
            errors.append(f"{eval_id} 引用不存在的 Prompt Pack：{prompt_pack}")

        character = str(item.get("character", ""))
        if character not in characters:
            errors.append(f"{eval_id} 引用不存在的角色：{character}")
        if pack and character and character != pack.get("character"):
            errors.append(f"{eval_id} character 与 prompt_pack 不一致：{character} != {pack.get('character')}")

        image_file = str(item.get("image_file", ""))
        if not image_file:
            errors.append(f"{eval_id} 缺少 image_file")
        elif image_file.startswith("/") or ".." in Path(image_file).parts:
            errors.append(f"{eval_id} image_file 不能是绝对路径或包含上级目录：{image_file}")
        else:
            image_path = root / image_file
            if image_path.suffix.lower() not in IMAGE_FILE_SUFFIXES:
                errors.append(f"{eval_id} image_file 必须是图片文件：{image_file}")
            elif not image_path.exists():
                errors.append(f"{eval_id} image_file 不存在：{image_file}")

        scores = item.get("scores")
        score_sum = 0
        if not isinstance(scores, dict):
            errors.append(f"{eval_id} scores 必须是 object")
        else:
            for key, max_value in SCORE_LIMITS.items():
                value = scores.get(key)
                if not isinstance(value, int):
                    errors.append(f"{eval_id} scores.{key} 必须是 integer")
                    continue
                if value < 0 or value > max_value:
                    errors.append(f"{eval_id} scores.{key} 必须在 0-{max_value}：{value}")
                score_sum += value
            extra_keys = sorted(set(scores) - set(SCORE_LIMITS))
            if extra_keys:
                errors.append(f"{eval_id} scores 存在未知字段：{', '.join(extra_keys)}")

        total_score = item.get("total_score")
        if not isinstance(total_score, int):
            errors.append(f"{eval_id} total_score 必须是 integer")
        elif total_score != score_sum:
            errors.append(f"{eval_id} total_score 应等于 scores 总和 {score_sum}，当前 {total_score}")

        public_safe = item.get("public_safe")
        if not isinstance(public_safe, bool):
            errors.append(f"{eval_id} public_safe 必须是 boolean")
        if public_safe is True and isinstance(scores, dict) and scores.get("public_safety", 0) < 12:
            warnings.append(f"{eval_id} public_safe=true，但 public_safety 低于 12")

        decision = str(item.get("decision", ""))
        if decision not in DECISIONS:
            errors.append(f"{eval_id} decision 必须是 {', '.join(sorted(DECISIONS))} 之一")
        if isinstance(total_score, int) and total_score >= 80 and decision in {"regenerate", "reject"}:
            warnings.append(f"{eval_id} 总分较高但 decision={decision}，请确认是否需要重生成或拒绝")

        failure_ids = item.get("failure_ids")
        if not isinstance(failure_ids, list):
            errors.append(f"{eval_id} failure_ids 必须是 array")
        else:
            seen_failure_ids: set[str] = set()
            for failure_id in failure_ids:
                if not isinstance(failure_id, str) or not failure_id.strip():
                    errors.append(f"{eval_id} failure_ids 不能包含空值")
                    continue
                if failure_id in seen_failure_ids:
                    errors.append(f"{eval_id} failure_ids 重复：{failure_id}")
                seen_failure_ids.add(failure_id)
                if failure_id not in failure_rule_ids:
                    errors.append(f"{eval_id} failure_ids 引用不存在的失败类型：{failure_id}")
            if decision in {"edit", "regenerate", "reject"} and not failure_ids:
                warnings.append(f"{eval_id} decision={decision}，建议填写 failure_ids 以便统计失败类型")

        issues = item.get("issues")
        if not isinstance(issues, list):
            errors.append(f"{eval_id} issues 必须是 array")
        next_action = str(item.get("next_action", ""))
        if not next_action.strip():
            errors.append(f"{eval_id} 缺少 next_action")

        rows.append([eval_id, prompt_pack, character, str(total_score), str(public_safe), decision])

    return EvaluationValidationResult(errors, warnings, rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate structured image output evaluation records.")
    parser.add_argument("--file", type=Path, default=DEFAULT_EVALUATIONS, help="Path to output evaluations JSON")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to prompt_packs.json")
    parser.add_argument("--failure-lexicon", type=Path, default=DEFAULT_FAILURE_FIX_LEXICON, help="Path to failure_fix_lexicon.json")
    parser.add_argument("--check", action="store_true", help="Validate and exit non-zero on errors")
    return parser.parse_args()


def main() -> int:
    configure_stdout()
    args = parse_args()
    document = load_json(args.file)
    config = load_config(args.config)
    failure_lexicon = load_json(args.failure_lexicon)
    result = validate_document(document, config, failure_lexicon=failure_lexicon)

    print("# 出图评分记录校验")
    print(f"文件：{args.file}")
    print(f"记录数：{len(document.get('evaluations', [])) if isinstance(document.get('evaluations'), list) else 0}")
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
    print("\nOK：出图评分记录校验通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
