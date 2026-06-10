from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from build_prompt_pack import DEFAULT_CONFIG, load_config
from check_prompt_repo import ROOT, classify_orientation, image_dimensions, reduced_aspect_ratio

DEFAULT_PREVIEW_DIR = ROOT / "预览图"
DEFAULT_MANIFEST = DEFAULT_PREVIEW_DIR / "manifest.json"
DIMENSION_FIELDS = ["width", "height", "aspect_ratio", "orientation"]
STANDARD_TAIL_FIELDS = ["character", "scene", "prompt_pack", "caption", "public_safe", "notes"]
MANIFEST_VERSION_RE = re.compile(r"^20[0-9]{2}-[0-9]{2}-[0-9]{2}-[a-z0-9][a-z0-9-]*$")
MANIFEST_FIELDS = {"$schema", "version", "description", "images"}
ENTRY_FIELDS = {"file", *DIMENSION_FIELDS, *STANDARD_TAIL_FIELDS}
IMAGE_NAME_RE = re.compile(r"^[^/\\]+\.(jpg|jpeg|png|webp)$", re.IGNORECASE)


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("manifest 根节点必须是 JSON object")
    return data


def validate_manifest(data: dict[str, Any], preview_dir: Path = DEFAULT_PREVIEW_DIR, config: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []

    extra_fields = sorted(set(data) - MANIFEST_FIELDS)
    if extra_fields:
        errors.append("预览图 manifest 存在未知顶层字段：" + ", ".join(extra_fields))
    for key in MANIFEST_FIELDS:
        if key not in data:
            errors.append(f"预览图 manifest 缺少字段：{key}")

    if data.get("$schema") != "manifest.schema.json":
        errors.append("预览图 manifest $schema 必须是 manifest.schema.json")

    version = data.get("version")
    if not isinstance(version, str) or not version.strip():
        errors.append("预览图 manifest 缺少 version")
    elif not MANIFEST_VERSION_RE.match(version):
        errors.append(f"预览图 manifest version 必须是日期前缀小写 slug：{version}")

    description = data.get("description")
    if not isinstance(description, str) or not description.strip():
        errors.append("预览图 manifest 缺少 description")

    entries = data.get("images")
    if not isinstance(entries, list) or not entries:
        errors.append("预览图 manifest.images 必须是非空 array")
        return errors

    pack_ids = set((config or {}).get("packs_by_id", {}))
    if config is not None and not pack_ids:
        pack_ids = {str(pack.get("id", "")) for pack in config.get("packs", []) if isinstance(pack, dict)}
    seen_files: set[str] = set()

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"预览图 manifest.images[{index}] 必须是 object")
            continue
        file_name = str(entry.get("file", ""))
        context = file_name or f"images[{index}]"

        extra_entry_fields = sorted(set(entry) - ENTRY_FIELDS)
        if extra_entry_fields:
            errors.append(f"预览图 manifest.{context} 存在未知字段：" + ", ".join(extra_entry_fields))
        if not file_name:
            errors.append(f"预览图 manifest.images[{index}] 缺少 file")
        elif not IMAGE_NAME_RE.match(file_name):
            errors.append(f"预览图 manifest.{file_name}.file 必须是 jpg/jpeg/png/webp 文件名")
        elif file_name in seen_files:
            errors.append(f"预览图 manifest file 重复：{file_name}")
        else:
            seen_files.add(file_name)
            if not (preview_dir / file_name).exists():
                errors.append(f"预览图 manifest 引用不存在的图片：{file_name}")

        for text_field in ["character", "scene", "caption", "notes"]:
            value = entry.get(text_field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"预览图 manifest.{context}.{text_field} 不能为空白")

        prompt_pack = entry.get("prompt_pack")
        if not isinstance(prompt_pack, str) or not prompt_pack.strip():
            errors.append(f"预览图 manifest.{context}.prompt_pack 不能为空白")
        elif config is not None and prompt_pack not in pack_ids:
            errors.append(f"预览图 manifest.{context}.prompt_pack 不存在：{prompt_pack}")

        if entry.get("public_safe") is not True:
            errors.append(f"预览图 manifest.{context}.public_safe 必须是 true")

    return errors


def ordered_entry(entry: dict[str, Any], width: int, height: int) -> dict[str, Any]:
    file_name = str(entry.get("file", ""))
    ordered: dict[str, Any] = {
        "file": file_name,
        "width": width,
        "height": height,
        "aspect_ratio": reduced_aspect_ratio(width, height),
        "orientation": classify_orientation(width, height),
    }
    for field in STANDARD_TAIL_FIELDS:
        if field in entry:
            ordered[field] = entry[field]
    for key, value in entry.items():
        if key not in ordered and key not in DIMENSION_FIELDS:
            ordered[key] = value
    return ordered


def sync_manifest(data: dict[str, Any], preview_dir: Path = DEFAULT_PREVIEW_DIR) -> dict[str, Any]:
    entries = data.get("images")
    if not isinstance(entries, list):
        raise ValueError("manifest.images 必须是 array")

    synced = dict(data)
    synced_entries: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"manifest.images[{index}] 必须是 object")
        file_name = str(entry.get("file", ""))
        if not file_name:
            raise ValueError(f"manifest.images[{index}] 缺少 file")
        if "/" in file_name or "\\" in file_name:
            raise ValueError(f"manifest.images[{index}].file 只能是文件名：{file_name}")

        image_path = preview_dir / file_name
        if not image_path.exists():
            raise FileNotFoundError(f"manifest 引用的图片不存在：{image_path}")
        width, height = image_dimensions(image_path)
        synced_entries.append(ordered_entry(entry, width, height))

    synced["images"] = synced_entries
    return synced


def render_manifest(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync preview image dimensions into 预览图/manifest.json.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="Path to preview manifest JSON.")
    parser.add_argument("--preview-dir", type=Path, default=DEFAULT_PREVIEW_DIR, help="Directory containing preview images.")
    parser.add_argument("--check", action="store_true", help="Only check whether manifest dimensions are current.")
    return parser.parse_args()


def main() -> int:
    configure_stdout()
    args = parse_args()

    try:
        manifest = load_manifest(args.manifest)
        config = load_config(DEFAULT_CONFIG)
        validation_errors = validate_manifest(manifest, args.preview_dir, config)
        if validation_errors:
            raise ValueError("；".join(validation_errors))
        synced = sync_manifest(manifest, args.preview_dir)
        current = args.manifest.read_text(encoding="utf-8")
        expected = render_manifest(synced)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR：预览图 manifest 尺寸同步失败：{exc}", file=sys.stderr)
        return 1

    if args.check:
        if current != expected:
            print("ERROR：预览图 manifest 尺寸元数据已过期，请运行：python 工具/sync_preview_manifest.py")
            return 1
        print("OK：预览图 manifest 尺寸元数据已同步。")
        return 0

    if current == expected:
        print("OK：预览图 manifest 尺寸元数据无需更新。")
        return 0

    args.manifest.write_text(expected, encoding="utf-8", newline="\n")
    print(f"OK：已同步预览图 manifest 尺寸元数据：{args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
