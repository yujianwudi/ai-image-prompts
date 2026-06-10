from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from build_prompt_pack import (
    DEFAULT_CONFIG,
    DEFAULT_OUTPUT_DIR,
    GENERATED_API_REQUESTS_JSONL,
    GENERATED_API_REQUESTS_SCHEMA,
    config_digest,
    load_config,
    render_api_request_payload,
    render_api_requests_jsonl,
    render_api_requests_schema,
)

DEFAULT_API_REQUESTS = DEFAULT_OUTPUT_DIR / GENERATED_API_REQUESTS_JSONL
DEFAULT_API_REQUESTS_SCHEMA = DEFAULT_OUTPUT_DIR / GENERATED_API_REQUESTS_SCHEMA


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_jsonl_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path} 第 {line_number} 行不是合法 JSON：{exc}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"{path} 第 {line_number} 行必须是 JSON object")
        records.append(record)
    return records


def validate_api_request_records(data: dict[str, Any], records: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    packs = [pack for pack in data.get("packs", []) if isinstance(pack, dict)]
    expected_ids = [str(pack.get("id", "")) for pack in packs]
    record_ids = [str(record.get("id", "")) for record in records]
    if record_ids != expected_ids:
        errors.append("API 请求 JSONL 的记录顺序或数量与配置中的 packs 不一致")

    characters = data.get("characters", {})
    templates = data.get("templates", {})
    digest = config_digest(data)
    pack_by_id = {str(pack.get("id", "")): pack for pack in packs}

    for record in records:
        pack_id = str(record.get("id", ""))
        pack = pack_by_id.get(pack_id)
        if not pack:
            errors.append(f"API 请求 JSONL 包含配置中不存在的 pack：{pack_id}")
            continue
        if record.get("source_config_sha256") != digest:
            errors.append(f"{pack_id}.source_config_sha256 与当前配置不一致")
        if record.get("character") != pack.get("character"):
            errors.append(f"{pack_id}.character 与配置不一致")
        if record.get("template") != pack.get("template"):
            errors.append(f"{pack_id}.template 与配置不一致")
        if pack.get("character") not in characters:
            errors.append(f"{pack_id} 引用了不存在的角色：{pack.get('character')}")
        if pack.get("template") not in templates:
            errors.append(f"{pack_id} 引用了不存在的模板：{pack.get('template')}")
        request = record.get("request")
        if not isinstance(request, dict):
            errors.append(f"{pack_id}.request 必须是 object")
            continue
        expected_request = render_api_request_payload(data, pack_id)
        if request != expected_request:
            errors.append(f"{pack_id}.request 与当前 Prompt Pack 渲染结果不一致")
        if request.get("model") != "gpt-image-2":
            errors.append(f"{pack_id}.request.model 必须是 gpt-image-2")
        if not str(request.get("prompt", "")).strip():
            errors.append(f"{pack_id}.request.prompt 不能为空")

    return errors


def validate_files(config_path: Path, jsonl_path: Path, schema_path: Path) -> list[str]:
    errors: list[str] = []
    data = load_config(config_path)

    if not schema_path.exists():
        errors.append(f"缺少 API 请求 JSONL schema：{schema_path}")
    else:
        actual_schema = schema_path.read_text(encoding="utf-8")
        expected_schema = render_api_requests_schema()
        if actual_schema != expected_schema:
            errors.append(f"API 请求 JSONL schema 已过期：{schema_path}")

    if not jsonl_path.exists():
        errors.append(f"缺少 API 请求 JSONL：{jsonl_path}")
        return errors

    actual_jsonl = jsonl_path.read_text(encoding="utf-8")
    expected_jsonl = render_api_requests_jsonl(data)
    if actual_jsonl != expected_jsonl:
        errors.append(f"API 请求 JSONL 已过期：{jsonl_path}")

    try:
        records = load_jsonl_records(jsonl_path)
    except ValueError as exc:
        errors.append(str(exc))
        return errors

    errors.extend(validate_api_request_records(data, records))
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate generated gpt-image-2 API request JSONL exports.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to prompt_packs.json")
    parser.add_argument("--jsonl", type=Path, default=DEFAULT_API_REQUESTS, help="Path to prompt_packs.api_requests.jsonl")
    parser.add_argument("--schema", type=Path, default=DEFAULT_API_REQUESTS_SCHEMA, help="Path to prompt_packs.api_requests.schema.json")
    parser.add_argument("--check", action="store_true", help="Return non-zero if generated API request files are stale or invalid")
    return parser.parse_args()


def main() -> int:
    configure_stdout()
    args = parse_args()
    config_path = args.config if args.config.is_absolute() else DEFAULT_CONFIG.parent.parent / args.config
    jsonl_path = args.jsonl if args.jsonl.is_absolute() else DEFAULT_OUTPUT_DIR.parent / args.jsonl
    schema_path = args.schema if args.schema.is_absolute() else DEFAULT_OUTPUT_DIR.parent / args.schema

    errors = validate_files(config_path, jsonl_path, schema_path)
    if errors:
        print("# API 请求 JSONL 校验")
        print(f"JSONL：{jsonl_path}")
        print(f"Schema：{schema_path}")
        print(f"错误：{len(errors)}")
        for error in errors:
            print(f"- {error}")
        return 1

    records = load_jsonl_records(jsonl_path)
    if args.check:
        print("OK：API 请求 JSONL 已同步。")
    else:
        print("# API 请求 JSONL 校验")
        print(f"JSONL：{jsonl_path}")
        print(f"Schema：{schema_path}")
        print(f"记录数：{len(records)}")
        print("错误：0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
