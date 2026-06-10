from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "配置" / "prompt_packs.json"
DEFAULT_OUTPUT_DIR = ROOT / "生成提示词"
GENERATED_JSON_BUNDLE = "prompt_packs.generated.json"
GENERATED_JSON_BUNDLE_SCHEMA = "prompt_packs.generated.schema.json"
GENERATED_CSV_INDEX = "prompt_packs.index.csv"
GENERATED_TAG_INDEX = "标签索引.md"

REQUIRED_CHARACTER_KEYS = ["display_name", "anchor", "must_keep", "avoid"]
REQUIRED_TEMPLATE_KEYS = ["task_type", "tags", "composition", "lighting", "material", "text_strategy", "safety"]
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
        tags = template.get("tags")
        if not isinstance(tags, list) or not tags:
            errors.append(f"templates.{template_id}.tags 必须是非空 array")
        elif any(not isinstance(tag, str) or not tag.strip() for tag in tags):
            errors.append(f"templates.{template_id}.tags 不能包含空值")
        elif "公开安全" not in tags:
            errors.append(f"templates.{template_id}.tags 必须包含 公开安全")

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


def render_pack_tags(data: dict[str, Any], pack: dict[str, Any]) -> list[str]:
    template = data["templates"][pack["template"]]
    raw_tags = [
        str(pack.get("character", "")),
        str(pack.get("template", "")),
        *[str(tag) for tag in template.get("tags", [])],
    ]
    tags: list[str] = []
    for tag in raw_tags:
        tag = tag.strip()
        if tag and tag not in tags:
            tags.append(tag)
    return tags


def render_pack_record(data: dict[str, Any], pack_id: str) -> dict[str, Any]:
    pack = get_pack(data, pack_id)
    char = data["characters"][pack["character"]]
    template = data["templates"][pack["template"]]
    return {
        "id": pack["id"],
        "title": pack["title"],
        "character": {
            "id": pack["character"],
            "display_name": char["display_name"],
            "must_keep": char["must_keep"],
            "avoid": char["avoid"],
        },
        "template": {
            "id": pack["template"],
            "task_type": template["task_type"],
            "tags": template.get("tags", []),
        },
        "tags": render_pack_tags(data, pack),
        "scene": pack["scene"],
        "action": pack["action"],
        "extra_constraints": pack.get("extra_constraints", []),
        "prompt": render_pack(data, pack_id),
    }


def config_digest(data: dict[str, Any]) -> str:
    canonical = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def render_json_bundle(data: dict[str, Any]) -> str:
    bundle = {
        "$schema": GENERATED_JSON_BUNDLE_SCHEMA,
        "source_config": "配置/prompt_packs.json",
        "source_config_sha256": config_digest(data),
        "generator": "工具/build_prompt_pack.py",
        "version": data.get("version", ""),
        "description": "Generated copy-ready Prompt Pack bundle. Do not edit by hand.",
        "pack_count": len(data.get("packs", [])),
        "characters": data.get("characters", {}),
        "templates": data.get("templates", {}),
        "packs": [render_pack_record(data, pack["id"]) for pack in data.get("packs", [])],
    }
    return json.dumps(bundle, ensure_ascii=False, indent=2) + "\n"


def render_csv_index(data: dict[str, Any]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["id", "title", "character_id", "character", "template_id", "template_type", "tags", "file"])
    characters = data.get("characters", {})
    templates = data.get("templates", {})
    for pack in data.get("packs", []):
        char = characters.get(pack.get("character"), {})
        template = templates.get(pack.get("template"), {})
        writer.writerow(
            [
                pack.get("id", ""),
                pack.get("title", ""),
                pack.get("character", ""),
                char.get("display_name", ""),
                pack.get("template", ""),
                template.get("task_type", ""),
                ";".join(render_pack_tags(data, pack)),
                generated_filename(str(pack.get("id", ""))),
            ]
        )
    return buffer.getvalue()


def generated_filename(pack_id: str) -> str:
    return f"{pack_id}.md"


def render_coverage_matrix(data: dict[str, Any]) -> str:
    templates = list(data.get("templates", {}).items())
    characters = list(data.get("characters", {}).items())
    pack_lookup: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for pack in data.get("packs", []):
        pack_lookup.setdefault((pack["character"], pack["template"]), []).append(pack)

    lines = [
        "# Prompt Pack 覆盖矩阵",
        "",
        "这个矩阵由 `工具/build_prompt_pack.py --all` 自动生成，用来观察每个角色已经覆盖了哪些输出类型。",
        "如果要补齐缺口，请优先修改 `配置/prompt_packs.json`，再重新导出。",
        "",
        "## 角色 × 输出类型",
        "",
    ]
    header = ["角色"] + [template["task_type"] for _, template in templates] + ["覆盖数量"]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")

    missing_lines: list[str] = []
    for char_id, char in characters:
        row = [char["display_name"]]
        count = 0
        missing: list[str] = []
        for template_id, template in templates:
            packs = pack_lookup.get((char_id, template_id), [])
            if packs:
                count += len(packs)
                links = [f"[`{pack['id']}`]({generated_filename(pack['id'])})" for pack in packs]
                row.append("<br>".join(links))
            else:
                row.append("—")
                missing.append(template["task_type"])
        row.append(str(count))
        lines.append("| " + " | ".join(row) + " |")
        if missing:
            missing_lines.append(f"- {char['display_name']}：" + "、".join(missing))

    lines.extend(["", "## 当前缺口", ""])
    if missing_lines:
        lines.extend(missing_lines)
    else:
        lines.append("所有角色已覆盖全部输出类型。")
    lines.append("")
    return "\n".join(lines)


def render_tag_index(data: dict[str, Any]) -> str:
    tag_map: dict[str, list[dict[str, Any]]] = {}
    for pack in data.get("packs", []):
        for tag in render_pack_tags(data, pack):
            tag_map.setdefault(tag, []).append(pack)

    lines = [
        "# Prompt Pack 标签索引",
        "",
        "这个索引由 `工具/build_prompt_pack.py --all` 自动生成，用来按 tag 快速查找 Prompt Pack。",
        "如果要修改标签，请优先修改 `配置/prompt_packs.json` 中的 `templates.*.tags`，再重新导出。",
        "",
        "## 使用命令",
        "",
        "```powershell",
        "python 工具/build_prompt_pack.py --tag 公开安全",
        "python 工具/build_prompt_pack.py --tag 商业海报",
        "```",
        "",
        "## 标签 × Prompt Pack",
        "",
        "| Tag | 数量 | Prompt Packs |",
        "| --- | ---: | --- |",
    ]
    for tag in sorted(tag_map):
        packs = tag_map[tag]
        links = [f"[`{pack['id']}`]({generated_filename(pack['id'])})" for pack in packs]
        lines.append(f"| `{tag}` | {len(packs)} | " + "<br>".join(links) + " |")
    lines.append("")
    return "\n".join(lines)


def render_generated_index(data: dict[str, Any]) -> str:
    templates = list(data.get("templates", {}).items())
    characters = list(data.get("characters", {}).items())
    pack_lookup = {(pack["character"], pack["template"]): pack for pack in data.get("packs", [])}

    lines = [
        "# 自动生成提示词",
        "",
        "这里的文件由 `工具/build_prompt_pack.py --all` 根据 `配置/prompt_packs.json` 生成。",
        "如果要修改内容，请优先修改配置，然后重新导出，不要手改生成文件。",
        "",
        "## 重新生成",
        "",
        "```powershell",
        "python 工具/run_quality_gate.py --refresh-generated",
        "```",
        "",
        "## 快速复制入口",
        "",
        "不知道选哪条时，按用途选：",
        "",
        "- **看角色是否串**：优先复制 `写实 cos 手机随手拍`。",
        "- **放 README 公开展示**：优先复制 `GitHub README 公开预览图`。",
        "- **检查发型、头饰、服装细节**：优先复制 `角色参考卡`。",
        "- **做宣传图或电商视觉**：优先复制 `商业联名海报 / 电商主图`。",
        "- **做教程封面**：优先复制 `竖版社媒封面缩略图`。",
        "",
        "### 按角色 × 用途",
        "",
    ]

    header = ["角色"] + [template["task_type"] for _, template in templates]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")
    for char_id, char in characters:
        row = [char["display_name"]]
        for template_id, _template in templates:
            pack = pack_lookup.get((char_id, template_id))
            if pack:
                filename = generated_filename(pack["id"])
                row.append(f"[`{pack['id']}`]({filename})")
            else:
                row.append("—")
        lines.append("| " + " | ".join(row) + " |")

    lines.extend(
        [
            "",
            "### 命令行复制",
            "",
            "```powershell",
            "python 工具/build_prompt_pack.py furina_convention_phone",
            "python 工具/build_prompt_pack.py citlali_readme_preview",
            "python 工具/build_prompt_pack.py dori_character_card",
            "```",
            "",
            "输出 Markdown 文件：",
            "",
            "```powershell",
            "python 工具/build_prompt_pack.py dori_commercial_poster --format markdown --out 示例/自动生成-多莉商业海报.md",
            "```",
            "",
            "输出 JSON 给脚本或前端使用：",
            "",
            "```powershell",
            "python 工具/build_prompt_pack.py furina_convention_phone --format json",
            "```",
        ]
    )

    lines.extend(
        [
        "",
        "## 覆盖矩阵",
        "",
        "- [`覆盖矩阵.md`](覆盖矩阵.md)：查看每个角色已覆盖/未覆盖的输出类型。",
        f"- [`{GENERATED_TAG_INDEX}`]({GENERATED_TAG_INDEX})：按 tags 查找 Prompt Pack。",
        f"- [`{GENERATED_JSON_BUNDLE}`]({GENERATED_JSON_BUNDLE})：全部 Prompt Pack 的机器可读 JSON bundle，包含 `source_config_sha256` 方便核对来源配置。",
        f"- [`{GENERATED_JSON_BUNDLE_SCHEMA}`]({GENERATED_JSON_BUNDLE_SCHEMA})：JSON bundle 的结构说明。",
        f"- [`{GENERATED_CSV_INDEX}`]({GENERATED_CSV_INDEX})：可用表格软件打开的 Prompt Pack 索引，含 tags 列方便筛选。",
        "",
        "## 文件列表",
        "",
        "| Prompt Pack | 文件 | 说明 |",
        "| --- | --- | --- |",
        ]
    )
    for pack in data.get("packs", []):
        pack_id = pack["id"]
        filename = generated_filename(pack_id)
        lines.append(f"| `{pack_id}` | `{filename}` | {pack['title']} |")
    lines.append("")
    return "\n".join(lines)


def export_all(data: dict[str, Any], out_dir: Path = DEFAULT_OUTPUT_DIR) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    index_path = out_dir / "README.md"
    index_path.write_text(render_generated_index(data), encoding="utf-8")
    written.append(index_path)
    matrix_path = out_dir / "覆盖矩阵.md"
    matrix_path.write_text(render_coverage_matrix(data), encoding="utf-8")
    written.append(matrix_path)
    tag_index_path = out_dir / GENERATED_TAG_INDEX
    tag_index_path.write_text(render_tag_index(data), encoding="utf-8")
    written.append(tag_index_path)
    json_bundle_path = out_dir / GENERATED_JSON_BUNDLE
    json_bundle_path.write_text(render_json_bundle(data), encoding="utf-8")
    written.append(json_bundle_path)
    csv_index_path = out_dir / GENERATED_CSV_INDEX
    csv_index_path.write_text(render_csv_index(data), encoding="utf-8")
    written.append(csv_index_path)
    expected_names = {"README.md", "覆盖矩阵.md", GENERATED_TAG_INDEX}
    for pack in data.get("packs", []):
        pack_id = pack["id"]
        filename = generated_filename(pack_id)
        expected_names.add(filename)
        path = out_dir / filename
        path.write_text(render_pack(data, pack_id, markdown=True), encoding="utf-8")
        written.append(path)
    for stale in out_dir.glob("*.md"):
        if stale.name not in expected_names:
            stale.unlink()
    return written


def list_packs(data: dict[str, Any]) -> str:
    rows = ["可用 Prompt Pack："]
    for pack in data.get("packs", []):
        char = data["characters"].get(pack.get("character"), {})
        template = data["templates"].get(pack.get("template"), {})
        rows.append(
            f"- {pack.get('id')}：{pack.get('title')} / {char.get('display_name', pack.get('character'))} / {template.get('task_type', pack.get('template'))}"
        )
    return "\n".join(rows) + "\n"


def list_packs_by_tag(data: dict[str, Any], tag: str) -> str:
    tag = tag.strip()
    rows = [f"匹配标签 `{tag}` 的 Prompt Pack："]
    matches = []
    for pack in data.get("packs", []):
        if tag in render_pack_tags(data, pack):
            matches.append(pack)
    if not matches:
        rows.append("- 未找到。可运行 `python 工具/build_prompt_pack.py --all` 后查看 `生成提示词/标签索引.md`。")
        return "\n".join(rows) + "\n"
    for pack in matches:
        char = data["characters"].get(pack.get("character"), {})
        template = data["templates"].get(pack.get("template"), {})
        filename = generated_filename(str(pack.get("id", "")))
        rows.append(
            f"- {pack.get('id')}：{pack.get('title')} / {char.get('display_name', pack.get('character'))} / {template.get('task_type', pack.get('template'))} / {filename}"
        )
    return "\n".join(rows) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a copy-ready prompt from 配置/prompt_packs.json")
    parser.add_argument("pack_id", nargs="?", help="Prompt Pack id, for example: furina_convention_phone")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to prompt_packs.json")
    parser.add_argument("--list", action="store_true", help="List available Prompt Packs")
    parser.add_argument("--tag", help="List Prompt Packs that contain an exact tag")
    parser.add_argument("--validate", action="store_true", help="Validate config and exit")
    parser.add_argument("--all", action="store_true", help="Export every Prompt Pack as Markdown")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory for --all exports")
    parser.add_argument("--format", choices=["text", "markdown", "json"], default="text", help="Output format")
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

    if args.tag:
        print(list_packs_by_tag(data, args.tag), end="")
        return 0

    if args.all:
        out_dir = args.out_dir if args.out_dir.is_absolute() else ROOT / args.out_dir
        written = export_all(data, out_dir)
        print(f"已导出 {len(written)} 个文件到：{out_dir}")
        for path in written:
            print(f"- {path}")
        return 0

    if not args.pack_id:
        print("请提供 pack_id，或使用 --list 查看可用组合。")
        return 2

    if args.format == "json":
        output = json.dumps(render_pack_record(data, args.pack_id), ensure_ascii=False, indent=2) + "\n"
    else:
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
