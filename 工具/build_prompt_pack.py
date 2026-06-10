from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "配置" / "prompt_packs.json"

REQUIRED_CHARACTER_KEYS = ["display_name", "anchor", "must_keep", "avoid"]
REQUIRED_TEMPLATE_KEYS = ["task_type", "composition", "lighting", "material", "text_strategy", "safety"]
REQUIRED_PACK_KEYS = ["id", "title", "character", "template", "scene", "action", "extra_constraints"]


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("配置根节点必须是 JSON object")
    return data


def _require_dict(data: dict[str, Any], key: str, errors: list[str]) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict) or not value:
        errors.append(f"{key} 必须是非空 object")
        return {}
    return value


def _require_list(data: dict[str, Any], key: str, errors: list[str]) -> list[Any]:
    value = data.get(key)
    if not isinstance(value, list) or not value:
        errors.append(f"{key} 必须是非空 array")
        return []
    return value


def validate_config(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    characters = _require_dict(data, "characters", errors)
    templates = _require_dict(data, "templates", errors)
    packs = _require_list(data, "packs", errors)
    global_constraints = _require_list(data, "global_quality_constraints", errors)

    for char_id, char in characters.items():
        if not isinstance(char, dict):
            errors.append(f"characters.{char_id} 必须是 object")
            continue
        for key in REQUIRED_CHARACTER_KEYS:
            if key not in char:
                errors.append(f"characters.{char_id} 缺少 {key}")
        if isinstance(char.get("must_keep"), list) and len(char["must_keep"]) < 3:
            errors.append(f"characters.{char_id}.must_keep 至少需要 3 个识别点")
        if isinstance(char.get("avoid"), list) and len(char["avoid"]) < 2:
            errors.append(f"characters.{char_id}.avoid 至少需要 2 个防串项")

    for template_id, template in templates.items():
        if not isinstance(template, dict):
            errors.append(f"templates.{template_id} 必须是 object")
            continue
        for key in REQUIRED_TEMPLATE_KEYS:
            if key not in template:
                errors.append(f"templates.{template_id} 缺少 {key}")
        safety = str(template.get("safety", ""))
        for term in ["非低俗", "不性感化"]:
            if term not in safety:
                errors.append(f"templates.{template_id}.safety 缺少 {term}")

    seen_pack_ids: set[str] = set()
    for index, pack in enumerate(packs):
        if not isinstance(pack, dict):
            errors.append(f"packs[{index}] 必须是 object")
            continue
        for key in REQUIRED_PACK_KEYS:
            if key not in pack:
                errors.append(f"packs[{index}] 缺少 {key}")
        pack_id = str(pack.get("id", ""))
        if not pack_id:
            continue
        if pack_id in seen_pack_ids:
            errors.append(f"packs id 重复：{pack_id}")
        seen_pack_ids.add(pack_id)
        if pack.get("character") not in characters:
            errors.append(f"packs.{pack_id} 引用了不存在的角色：{pack.get('character')}")
        if pack.get("template") not in templates:
            errors.append(f"packs.{pack_id} 引用了不存在的模板：{pack.get('template')}")
        if not isinstance(pack.get("extra_constraints"), list):
            errors.append(f"packs.{pack_id}.extra_constraints 必须是 array")

    joined_global = "\n".join(str(item) for item in global_constraints)
    for term in ["不要混入", "不要水印", "不插画风"]:
        if term not in joined_global:
            errors.append(f"global_quality_constraints 缺少 {term}")

    return errors


def get_pack(data: dict[str, Any], pack_id: str) -> dict[str, Any]:
    for pack in data.get("packs", []):
        if pack.get("id") == pack_id:
            return pack
    available = ", ".join(pack.get("id", "") for pack in data.get("packs", []))
    raise KeyError(f"找不到 pack：{pack_id}。可用：{available}")


def render_pack(data: dict[str, Any], pack_id: str, markdown: bool = False) -> str:
    pack = get_pack(data, pack_id)
    char = data["characters"][pack["character"]]
    template = data["templates"][pack["template"]]

    lines: list[str] = []
    if markdown:
        lines.append(f"# {pack['title']}")
        lines.append("")
        lines.append("```text")

    lines.extend(
        [
            f"生成一张{template['task_type']}图像。",
            "",
            "主体锁定：",
            char["anchor"],
            "",
            "必须保留：",
        ]
    )
    lines.extend(f"- {item}" for item in char["must_keep"])
    lines.extend(["", "场景环境：", pack["scene"], "", "动作/表情：", pack["action"], ""])
    lines.extend(
        [
            "版式构图：",
            template["composition"],
            "",
            "光线色彩：",
            template["lighting"],
            "",
            "材质细节：",
            template["material"],
            "",
            "文字策略：",
            template["text_strategy"],
            "",
            "安全约束：",
            template["safety"],
            "",
            "防串约束：",
        ]
    )
    lines.extend(f"- 不要混入{item}" for item in char["avoid"])
    lines.extend(f"- {item}" for item in pack.get("extra_constraints", []))
    lines.extend(["", "质量约束："])
    lines.extend(f"- {item}" for item in data.get("global_quality_constraints", []))

    if markdown:
        lines.append("```")
    return "\n".join(lines).rstrip() + "\n"


def list_packs(data: dict[str, Any]) -> str:
    rows = ["可用 Prompt Pack："]
    for pack in data.get("packs", []):
        char = data["characters"].get(pack.get("character"), {})
        template = data["templates"].get(pack.get("template"), {})
        rows.append(
            f"- {pack.get('id')}：{pack.get('title')} / {char.get('display_name', pack.get('character'))} / {template.get('task_type', pack.get('template'))}"
        )
    return "\n".join(rows) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a copy-ready prompt from 配置/prompt_packs.json")
    parser.add_argument("pack_id", nargs="?", help="Prompt Pack id, for example: furina_convention_phone")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to prompt_packs.json")
    parser.add_argument("--list", action="store_true", help="List available Prompt Packs")
    parser.add_argument("--validate", action="store_true", help="Validate config and exit")
    parser.add_argument("--format", choices=["text", "markdown"], default="text", help="Output format")
    parser.add_argument("--out", type=Path, help="Write output to a file")
    return parser.parse_args()


def main() -> int:
    configure_stdout()
    args = parse_args()
    data = load_config(args.config)
    errors = validate_config(data)
    if errors:
        print("配置校验失败：")
        for item in errors:
            print(f"- {item}")
        return 1

    if args.validate:
        print("OK：Prompt Pack 配置通过校验。")
        return 0

    if args.list:
        print(list_packs(data), end="")
        return 0

    if not args.pack_id:
        print("请提供 pack_id，或使用 --list 查看可用组合。")
        return 2

    output = render_pack(data, args.pack_id, markdown=args.format == "markdown")
    if args.out:
        out_path = args.out if args.out.is_absolute() else ROOT / args.out
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(f"已写入：{out_path}")
    else:
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
