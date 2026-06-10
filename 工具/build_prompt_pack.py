from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from pathlib import Path
from typing import Any

from validate_gpt_image2_parameters import validate_size_spec

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "配置" / "prompt_packs.json"
DEFAULT_TAG_TAXONOMY = ROOT / "配置" / "tag_taxonomy.json"
DEFAULT_OUTPUT_DIR = ROOT / "生成提示词"
GENERATED_JSON_BUNDLE = "prompt_packs.generated.json"
GENERATED_JSON_BUNDLE_SCHEMA = "prompt_packs.generated.schema.json"
GENERATED_CSV_INDEX = "prompt_packs.index.csv"
GENERATED_TAG_INDEX = "标签索引.md"
GENERATED_TAG_COVERAGE_MATRIX = "标签覆盖矩阵.md"

REQUIRED_CHARACTER_KEYS = ["display_name", "anchor", "must_keep", "avoid"]
REQUIRED_TEMPLATE_KEYS = [
    "task_type",
    "tags",
    "api_profile",
    "composition",
    "lighting",
    "material",
    "text_strategy",
    "safety",
]
REQUIRED_PACK_KEYS = ["id", "title", "character", "template", "scene", "action", "extra_constraints"]
API_PROFILE_ORDER = ["model", "size", "quality", "output_format", "output_compression", "background"]
VALID_API_QUALITIES = {"low", "medium", "high", "auto"}
VALID_API_OUTPUT_FORMATS = {"png", "jpeg", "webp"}


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("配置根节点必须是 JSON object")
    return data


def load_tag_taxonomy(path: Path = DEFAULT_TAG_TAXONOMY) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("标签词表根节点必须是 JSON object")
    return data


def validate_tag_taxonomy(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("$schema") != "tag_taxonomy.schema.json":
        errors.append("tag_taxonomy.json 的 $schema 应为 tag_taxonomy.schema.json")
    if not str(data.get("version", "")).strip():
        errors.append("tag_taxonomy.json 缺少 version")

    categories = data.get("categories")
    if not isinstance(categories, list) or not categories:
        errors.append("tag_taxonomy.json categories 必须是非空 array")
        categories = []
    category_ids: set[str] = set()
    for index, category in enumerate(categories):
        if not isinstance(category, dict):
            errors.append(f"tag_taxonomy.categories[{index}] 必须是 object")
            continue
        category_id = str(category.get("id", "")).strip()
        if not category_id:
            errors.append(f"tag_taxonomy.categories[{index}].id 不能为空")
            continue
        if category_id in category_ids:
            errors.append(f"tag_taxonomy category id 重复：{category_id}")
        category_ids.add(category_id)
        for key in ["name", "description"]:
            if not str(category.get(key, "")).strip():
                errors.append(f"tag_taxonomy.categories.{category_id}.{key} 不能为空")

    tags = data.get("tags")
    if not isinstance(tags, list) or not tags:
        errors.append("tag_taxonomy.json tags 必须是非空 array")
        tags = []
    tag_ids: set[str] = set()
    alias_to_tag: dict[str, str] = {}
    for index, tag in enumerate(tags):
        if not isinstance(tag, dict):
            errors.append(f"tag_taxonomy.tags[{index}] 必须是 object")
            continue
        tag_id = str(tag.get("id", "")).strip()
        if not tag_id:
            errors.append(f"tag_taxonomy.tags[{index}].id 不能为空")
            continue
        if tag_id in tag_ids:
            errors.append(f"tag_taxonomy tag id 重复：{tag_id}")
        tag_ids.add(tag_id)
        category = str(tag.get("category", "")).strip()
        if category not in category_ids:
            errors.append(f"tag_taxonomy.tags.{tag_id}.category 未登记：{category}")
        if not str(tag.get("description", "")).strip():
            errors.append(f"tag_taxonomy.tags.{tag_id}.description 不能为空")
        aliases = tag.get("aliases", [])
        if aliases is None:
            aliases = []
        if not isinstance(aliases, list):
            errors.append(f"tag_taxonomy.tags.{tag_id}.aliases 必须是 array")
            continue
        for alias in aliases:
            alias = str(alias).strip()
            if not alias:
                errors.append(f"tag_taxonomy.tags.{tag_id}.aliases 不能包含空值")
                continue
            if alias == tag_id:
                errors.append(f"tag_taxonomy.tags.{tag_id}.aliases 不应重复主标签")
            if alias in tag_ids:
                errors.append(f"tag_taxonomy alias 已经是正式标签：{alias}")
            previous = alias_to_tag.get(alias)
            if previous and previous != tag_id:
                errors.append(f"tag_taxonomy alias 重复：{alias} 同时指向 {previous} 和 {tag_id}")
            alias_to_tag[alias] = tag_id

    if "公开安全" not in tag_ids:
        errors.append("tag_taxonomy.json 必须登记 公开安全")
    return errors


def taxonomy_tag_ids(data: dict[str, Any]) -> set[str]:
    return {str(tag.get("id", "")).strip() for tag in data.get("tags", []) if isinstance(tag, dict)}


def taxonomy_aliases(data: dict[str, Any]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for tag in data.get("tags", []):
        if not isinstance(tag, dict):
            continue
        tag_id = str(tag.get("id", "")).strip()
        for alias in tag.get("aliases", []) or []:
            alias = str(alias).strip()
            if alias and tag_id:
                aliases[alias] = tag_id
    return aliases


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


def validate_api_profile(profile: Any, context: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(profile, dict):
        return [f"{context}.api_profile 必须是 object"]

    required = ["model", "size", "quality", "output_format", "background"]
    for key in required:
        if key not in profile:
            errors.append(f"{context}.api_profile 缺少 {key}")

    if profile.get("model") != "gpt-image-2":
        errors.append(f"{context}.api_profile.model 必须是 gpt-image-2")

    size = str(profile.get("size", "")).strip()
    if not size:
        errors.append(f"{context}.api_profile.size 不能为空")
    else:
        try:
            validation = validate_size_spec(size, require_9_16=True)
        except ValueError as exc:
            errors.append(f"{context}.api_profile.size 格式错误：{exc}")
        else:
            for item in validation.errors:
                errors.append(f"{context}.api_profile.size 不符合 gpt-image-2 规格：{item}")
            for item in validation.warnings:
                errors.append(f"{context}.api_profile.size 不符合本仓库 9:16 竖图约定：{item}")

    quality = profile.get("quality")
    if quality not in VALID_API_QUALITIES:
        errors.append(f"{context}.api_profile.quality 必须是 low / medium / high / auto")

    output_format = profile.get("output_format")
    if output_format not in VALID_API_OUTPUT_FORMATS:
        errors.append(f"{context}.api_profile.output_format 必须是 png / jpeg / webp")

    compression = profile.get("output_compression")
    if output_format in {"jpeg", "webp"}:
        if type(compression) is not int or not 0 <= compression <= 100:
            errors.append(f"{context}.api_profile.output_compression 在 jpeg/webp 时必须是 0-100 的整数")
    elif output_format == "png" and "output_compression" in profile:
        errors.append(f"{context}.api_profile.output_compression 不应和 png 一起使用")

    if profile.get("background") != "opaque":
        errors.append(f"{context}.api_profile.background 必须是 opaque")

    return errors


def validate_config(data: dict[str, Any], tag_taxonomy: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    characters = _require_dict(data, "characters", errors)
    templates = _require_dict(data, "templates", errors)
    packs = _require_list(data, "packs", errors)
    global_constraints = _require_list(data, "global_quality_constraints", errors)
    known_tags: set[str] = set()
    tag_aliases: dict[str, str] = {}

    if tag_taxonomy is None:
        if DEFAULT_TAG_TAXONOMY.exists():
            try:
                tag_taxonomy = load_tag_taxonomy(DEFAULT_TAG_TAXONOMY)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"无法读取标签词表：{exc}")
        else:
            errors.append("缺少标签词表：配置/tag_taxonomy.json")
    if tag_taxonomy is not None:
        errors.extend(validate_tag_taxonomy(tag_taxonomy))
        known_tags = taxonomy_tag_ids(tag_taxonomy)
        tag_aliases = taxonomy_aliases(tag_taxonomy)

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
        errors.extend(validate_api_profile(template.get("api_profile"), f"templates.{template_id}"))
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
        if isinstance(tags, list):
            for tag in tags:
                tag_text = str(tag).strip()
                if not tag_text:
                    continue
                if known_tags and tag_text not in known_tags:
                    if tag_text in tag_aliases:
                        errors.append(f"templates.{template_id}.tags 使用了别名 {tag_text}，请改为正式标签 {tag_aliases[tag_text]}")
                    else:
                        errors.append(f"templates.{template_id}.tags 未登记到 配置/tag_taxonomy.json：{tag_text}")

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


def format_api_profile(profile: dict[str, Any]) -> str:
    lines = []
    for key in API_PROFILE_ORDER:
        if key in profile:
            lines.append(f"{key}: {profile[key]}")
    return "\n".join(lines)


def render_pack(data: dict[str, Any], pack_id: str, markdown: bool = False) -> str:
    pack = get_pack(data, pack_id)
    char = data["characters"][pack["character"]]
    template = data["templates"][pack["template"]]

    lines: list[str] = []
    if markdown:
        lines.append(f"# {pack['title']}")
        lines.append("")
        lines.append("## 推荐 API 参数")
        lines.append("")
        lines.append("```yaml")
        lines.append(format_api_profile(template["api_profile"]))
        lines.append("```")
        lines.append("")
        lines.append("## 提示词")
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
    api_profile = dict(template["api_profile"])
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
            "api_profile": api_profile,
        },
        "api_profile": api_profile,
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
    writer.writerow(
        [
            "id",
            "title",
            "character_id",
            "character",
            "template_id",
            "template_type",
            "api_model",
            "api_size",
            "api_quality",
            "api_output_format",
            "api_output_compression",
            "api_background",
            "tags",
            "file",
        ]
    )
    characters = data.get("characters", {})
    templates = data.get("templates", {})
    for pack in data.get("packs", []):
        char = characters.get(pack.get("character"), {})
        template = templates.get(pack.get("template"), {})
        api_profile = template.get("api_profile", {})
        writer.writerow(
            [
                pack.get("id", ""),
                pack.get("title", ""),
                pack.get("character", ""),
                char.get("display_name", ""),
                pack.get("template", ""),
                template.get("task_type", ""),
                api_profile.get("model", ""),
                api_profile.get("size", ""),
                api_profile.get("quality", ""),
                api_profile.get("output_format", ""),
                api_profile.get("output_compression", ""),
                api_profile.get("background", ""),
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


def render_tag_coverage_matrix(data: dict[str, Any], tag_taxonomy: dict[str, Any] | None = None) -> str:
    if tag_taxonomy is None:
        tag_taxonomy = load_tag_taxonomy(DEFAULT_TAG_TAXONOMY) if DEFAULT_TAG_TAXONOMY.exists() else {"tags": []}

    characters = data.get("characters", {})
    templates = data.get("templates", {})
    packs = data.get("packs", [])

    category_names = {
        str(category.get("id", "")): str(category.get("name", category.get("id", "")))
        for category in tag_taxonomy.get("categories", [])
        if isinstance(category, dict)
    }
    official_tags = [tag for tag in tag_taxonomy.get("tags", []) if isinstance(tag, dict)]
    official_tag_ids = [str(tag.get("id", "")).strip() for tag in official_tags if str(tag.get("id", "")).strip()]
    used_tag_ids = sorted({str(tag) for template in templates.values() for tag in template.get("tags", [])})
    tag_order = official_tag_ids + [tag for tag in used_tag_ids if tag not in official_tag_ids]

    tag_meta = {str(tag.get("id", "")).strip(): tag for tag in official_tags}

    lines = [
        "# Prompt Pack 标签覆盖矩阵",
        "",
        "这个矩阵由 `工具/build_prompt_pack.py --all` 自动生成，用来检查 tags 在模板、角色和 Prompt Pack 中的覆盖情况。",
        "新增标签前请先登记到 `配置/tag_taxonomy.json`，再写入 `配置/prompt_packs.json`。",
        "",
        "## Tag × 角色覆盖",
        "",
    ]
    header = ["Tag", "分类", "模板数量", "Prompt Pack 数量"] + [char["display_name"] for char in characters.values()] + ["模板"]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")

    unused_tags: list[str] = []
    for tag_id in tag_order:
        tagged_templates = [
            (template_id, template)
            for template_id, template in templates.items()
            if tag_id in template.get("tags", [])
        ]
        tagged_template_ids = {template_id for template_id, _template in tagged_templates}
        tagged_packs = [pack for pack in packs if str(pack.get("template", "")) in tagged_template_ids]
        char_counts = {
            char_id: sum(1 for pack in tagged_packs if pack.get("character") == char_id)
            for char_id in characters
        }
        if not tagged_templates:
            unused_tags.append(tag_id)
        meta = tag_meta.get(tag_id, {})
        category_id = str(meta.get("category", "未登记"))
        category = category_names.get(category_id, category_id)
        template_links = [
            f"`{template_id}`"
            for template_id, _template in tagged_templates
        ]
        row = [
            f"`{tag_id}`",
            category,
            str(len(tagged_templates)),
            str(len(tagged_packs)),
            *[str(char_counts[char_id]) for char_id in characters],
            "<br>".join(template_links) if template_links else "—",
        ]
        lines.append("| " + " | ".join(row) + " |")

    lines.extend(["", "## 未使用的正式标签", ""])
    if unused_tags:
        lines.extend(f"- `{tag}`" for tag in unused_tags)
    else:
        lines.append("无。")
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
            "",
            "每个 Markdown 文件顶部都会给出 `gpt-image-2` 推荐 API 参数；纯文本输出仍只保留可复制提示词，JSON 输出会包含 `api_profile`，方便脚本直接取 `model` / `size` / `quality` / `output_format`。",
        ]
    )

    lines.extend(
        [
            "",
            "## 覆盖矩阵",
            "",
            "- [`覆盖矩阵.md`](覆盖矩阵.md)：查看每个角色已覆盖/未覆盖的输出类型。",
            f"- [`{GENERATED_TAG_INDEX}`]({GENERATED_TAG_INDEX})：按 tags 查找 Prompt Pack。",
            f"- [`{GENERATED_TAG_COVERAGE_MATRIX}`]({GENERATED_TAG_COVERAGE_MATRIX})：查看每个正式 tag 覆盖了哪些模板、角色和 Prompt Pack。",
            f"- [`{GENERATED_JSON_BUNDLE}`]({GENERATED_JSON_BUNDLE})：全部 Prompt Pack 的机器可读 JSON bundle，包含 `source_config_sha256`、tags 和 `api_profile` 方便核对来源配置并直接接 API。",
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
    tag_coverage_path = out_dir / GENERATED_TAG_COVERAGE_MATRIX
    tag_coverage_path.write_text(render_tag_coverage_matrix(data), encoding="utf-8")
    written.append(tag_coverage_path)
    json_bundle_path = out_dir / GENERATED_JSON_BUNDLE
    json_bundle_path.write_text(render_json_bundle(data), encoding="utf-8")
    written.append(json_bundle_path)
    csv_index_path = out_dir / GENERATED_CSV_INDEX
    csv_index_path.write_text(render_csv_index(data), encoding="utf-8")
    written.append(csv_index_path)
    expected_names = {"README.md", "覆盖矩阵.md", GENERATED_TAG_INDEX, GENERATED_TAG_COVERAGE_MATRIX}
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
