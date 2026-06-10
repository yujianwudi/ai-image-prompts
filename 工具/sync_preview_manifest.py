from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from check_prompt_repo import ROOT, classify_orientation, image_dimensions, reduced_aspect_ratio

DEFAULT_PREVIEW_DIR = ROOT / "预览图"
DEFAULT_MANIFEST = DEFAULT_PREVIEW_DIR / "manifest.json"
DIMENSION_FIELDS = ["width", "height", "aspect_ratio", "orientation"]
STANDARD_TAIL_FIELDS = ["character", "scene", "prompt_pack", "caption", "public_safe", "notes"]


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("manifest 根节点必须是 JSON object")
    return data


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

    args.manifest.write_text(expected, encoding="utf-8")
    print(f"OK：已同步预览图 manifest 尺寸元数据：{args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
