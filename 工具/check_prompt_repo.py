from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

from build_prompt_pack import (
    GENERATED_JSON_BUNDLE,
    GENERATED_JSON_BUNDLE_SCHEMA,
    generated_filename,
    load_config,
    render_coverage_matrix,
    render_generated_index,
    render_json_bundle,
    render_pack,
    validate_config,
)

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DIRS = [
    "角色",
    "模板",
    "示例",
    "评估",
    "参考仓库",
    "工具",
    "预览图",
    "配置",
    "生成提示词",
    "tests",
]

REQUIRED_FILES = [
    "README.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "免责声明.md",
    "授权与使用边界.md",
    "内容安全政策.md",
    "SECURITY.md",
    ".editorconfig",
    ".gitattributes",
    ".gitignore",
    "角色/README.md",
    "模板/README.md",
    "模板/01-固定模板-室内漫展手机随手拍.md",
    "模板/02-gpt-image-2-提示词优化指南.md",
    "模板/05-Prompt-as-Code字段模板.md",
    "模板/16-封面缩略图模板.md",
    "模板/17-长图教程Slides模板.md",
    "模板/18-地图导览模板.md",
    "示例/README.md",
    "评估/README.md",
    "评估/角色防串审计报告.md",
    "参考仓库/README.md",
    "参考仓库/仓库追踪清单.md",
    "参考仓库/分类映射表.md",
    "参考仓库/持续优化流程.md",
    "工具/README.md",
    "工具/refresh_reference_summary.py",
    "工具/audit_character_prompts.py",
    "工具/build_prompt_pack.py",
    "工具/run_quality_gate.py",
    "配置/README.md",
    "配置/prompt_packs.json",
    "配置/prompt_packs.schema.json",
    "预览图/README.md",
    "预览图/manifest.json",
    "预览图/manifest.schema.json",
    "生成提示词/README.md",
    "生成提示词/prompt_packs.generated.schema.json",
    "tests/test_prompt_pack_tools.py",
    ".github/workflows/validate.yml",
    ".github/ISSUE_TEMPLATE/output_issue.yml",
    ".github/ISSUE_TEMPLATE/template_optimization.yml",
    ".github/ISSUE_TEMPLATE/character_prompt.yml",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
]

REFERENCE_REPOS = [
    "EvoLinkAI/awesome-gpt-image-2-API-and-Prompts",
    "freestylefly/awesome-gpt-image-2",
    "YouMind-OpenLab/awesome-gpt-image-2",
]

LOCAL_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
HTML_SRC_RE = re.compile(r"src=[\"']([^\"']+)[\"']")
C1_CONTROL_RE = re.compile(r"[\u0080-\u009f]")
TEXT_SCAN_SUFFIXES = {".md", ".py", ".json", ".yml", ".yaml", ".txt"}
TEXT_SCAN_NAMES = {".gitignore", ".gitattributes", ".editorconfig"}
SECRET_PATTERNS = [
    ("OpenAI API key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("GitHub fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    (
        "generic assigned secret",
        re.compile(r"(?i)\b(api[_-]?key|secret|token|password)\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{24,}"),
    ),
]


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def is_external(target: str) -> bool:
    lowered = target.lower()
    return (
        lowered.startswith("http://")
        or lowered.startswith("https://")
        or lowered.startswith("mailto:")
        or lowered.startswith("#")
        or lowered.startswith("data:")
    )


def clean_target(target: str) -> str:
    target = target.strip()
    target = target.split("#", 1)[0]
    target = target.split("?", 1)[0]
    return unquote(target)


def check_readme_badges(errors: list[str]) -> None:
    readme_path = ROOT / "README.md"
    config_path = ROOT / "配置" / "prompt_packs.json"
    if not readme_path.exists() or not config_path.exists():
        return
    readme = readme_path.read_text(encoding="utf-8")
    try:
        data = load_config(config_path)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"无法检查 README 徽章：{exc}")
        return
    template_count = len([path for path in (ROOT / "模板").glob("*.md") if path.name.lower() != "readme.md"])
    expected = {
        "CI badge": "actions/workflows/validate.yml/badge.svg",
        "Prompt Packs badge": f"Prompt%20Packs-{len(data.get('packs', []))}-",
        "Characters badge": f"Characters-{len(data.get('characters', {}))}-",
        "Templates badge": f"Templates-{template_count}-",
        "JSON Schema badge": "JSON%20Schema-enabled",
    }
    for label, needle in expected.items():
        if needle not in readme:
            errors.append(f"README 徽章缺失或数字过期：{label} 应包含 {needle}")


def check_repo_style_config(errors: list[str]) -> None:
    gitattributes = ROOT / ".gitattributes"
    editorconfig = ROOT / ".editorconfig"
    gitignore = ROOT / ".gitignore"
    if gitattributes.exists():
        text = gitattributes.read_text(encoding="utf-8")
        for required in ["* text=auto eol=lf", "*.md text eol=lf", "*.py text eol=lf", "*.json text eol=lf", "*.jpg binary"]:
            if required not in text:
                errors.append(f".gitattributes 缺少规则：{required}")
    if editorconfig.exists():
        text = editorconfig.read_text(encoding="utf-8")
        for required in ["charset = utf-8", "end_of_line = lf", "insert_final_newline = true"]:
            if required not in text:
                errors.append(f".editorconfig 缺少规则：{required}")
    if gitignore.exists():
        text = gitignore.read_text(encoding="utf-8")
        for required in ["__pycache__/", "*.py[cod]", ".venv/", ".env", "原图/", "*.psd", ".DS_Store", "Thumbs.db"]:
            if required not in text:
                errors.append(f".gitignore 缺少规则：{required}")


def check_required_dirs(errors: list[str]) -> None:
    for item in REQUIRED_DIRS:
        path = ROOT / item
        if not path.is_dir():
            errors.append(f"缺少目录：{item}")


def check_required_files(errors: list[str]) -> None:
    for item in REQUIRED_FILES:
        path = ROOT / item
        if not path.is_file():
            errors.append(f"缺少文件：{item}")


def check_markdown_health(errors: list[str], warnings: list[str]) -> None:
    for path in sorted(ROOT.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            errors.append(f"Markdown 文件为空：{rel(path)}")
        if "\ufffd" in text or C1_CONTROL_RE.search(text):
            errors.append(f"疑似编码损坏：{rel(path)}")
        if len(text.splitlines()) > 800:
            warnings.append(f"Markdown 文件较长，建议拆分：{rel(path)}")


def check_local_links(errors: list[str]) -> None:
    for path in sorted(ROOT.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        targets = [m.group(1) for m in LOCAL_LINK_RE.finditer(text)]
        targets.extend(m.group(1) for m in HTML_SRC_RE.finditer(text))
        for raw in targets:
            if is_external(raw):
                continue
            target = clean_target(raw)
            if not target:
                continue
            candidate = (path.parent / target).resolve()
            try:
                candidate.relative_to(ROOT.resolve())
            except ValueError:
                errors.append(f"本地链接越界：{rel(path)} -> {raw}")
                continue
            if not candidate.exists():
                errors.append(f"本地链接不存在：{rel(path)} -> {raw}")


def check_secret_leaks(errors: list[str]) -> None:
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        parts = set(path.parts)
        if ".git" in parts or "__pycache__" in parts:
            continue
        if path.suffix.lower() not in TEXT_SCAN_SUFFIXES and path.name not in TEXT_SCAN_NAMES:
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"无法扫描文本文件是否含密钥：{rel(path)} ({exc})")
            continue
        for line_number, line in enumerate(lines, start=1):
            for label, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    errors.append(f"疑似密钥泄露：{rel(path)}:{line_number} ({label})")


def check_content_safety_policy(errors: list[str]) -> None:
    path = ROOT / "内容安全政策.md"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    for term in ["非低俗", "不性感化", "不儿童化", "真实个人隐私", "不要真实品牌 logo", "不要混入其他角色元素"]:
        if term not in text:
            errors.append(f"内容安全政策缺少关键约束：{term}")
    security = ROOT / "SECURITY.md"
    if security.exists():
        security_text = security.read_text(encoding="utf-8")
        if "内容安全政策.md" not in security_text:
            errors.append("SECURITY.md 应指向 内容安全政策.md")
        if "授权与使用边界.md" not in security_text:
            errors.append("SECURITY.md 应指向 授权与使用边界.md")
    usage_boundary = ROOT / "授权与使用边界.md"
    if usage_boundary.exists():
        text = usage_boundary.read_text(encoding="utf-8")
        for term in ["不是法律意见", "第三方 IP", "不代表官方授权", "预览图", "商用", "LICENSE"]:
            if term not in text:
                errors.append(f"授权与使用边界缺少关键说明：{term}")


def check_github_workflow(errors: list[str]) -> None:
    path = ROOT / ".github" / "workflows" / "validate.yml"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    if "工具/run_quality_gate.py" not in text:
        errors.append("GitHub Actions 应调用统一质量门禁：python 工具/run_quality_gate.py")


def check_role_safety(errors: list[str]) -> None:
    role_dir = ROOT / "角色"
    for path in sorted(role_dir.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        text = path.read_text(encoding="utf-8")
        for term in ["非低俗", "不性感化", "不要混入"]:
            if term not in text:
                errors.append(f"角色文件缺少必要约束“{term}”：{rel(path)}")


def check_reference_tracking(errors: list[str]) -> None:
    path = ROOT / "参考仓库" / "仓库追踪清单.md"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    for repo in REFERENCE_REPOS:
        if repo not in text:
            errors.append(f"参考仓库追踪清单缺少：{repo}")


def check_preview_images(errors: list[str], warnings: list[str]) -> None:
    preview_dir = ROOT / "预览图"
    if not preview_dir.exists():
        errors.append("缺少预览图目录")
        return
    images = sorted(
        [p for p in preview_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]
    )
    if not images:
        warnings.append("预览图目录为空，README 展示效果会弱")
    for image in images:
        if image.stat().st_size > 2 * 1024 * 1024:
            warnings.append(f"预览图超过 2MB，建议压缩：{rel(image)}")

    manifest_path = preview_dir / "manifest.json"
    if not manifest_path.exists():
        errors.append("缺少预览图清单：预览图/manifest.json")
        return
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"预览图清单无法读取：{exc}")
        return
    check_preview_manifest_schema(manifest, errors)

    entries = manifest.get("images")
    if not isinstance(entries, list) or not entries:
        errors.append("预览图清单 images 必须是非空 array")
        return

    actual_files = {image.name for image in images}
    manifest_files: set[str] = set()
    pack_ids: set[str] = set()
    config_path = ROOT / "配置" / "prompt_packs.json"
    if config_path.exists():
        try:
            pack_ids = {pack.get("id", "") for pack in load_config(config_path).get("packs", [])}
        except Exception as exc:  # noqa: BLE001
            errors.append(f"无法读取 Prompt Pack 配置以校验预览图：{exc}")

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"预览图清单 images[{index}] 必须是 object")
            continue
        file_name = str(entry.get("file", ""))
        if not file_name:
            errors.append(f"预览图清单 images[{index}] 缺少 file")
            continue
        manifest_files.add(file_name)
        if "/" in file_name or "\\" in file_name:
            errors.append(f"预览图清单 file 只能是文件名：{file_name}")
        if file_name not in actual_files:
            errors.append(f"预览图清单引用不存在的图片：{file_name}")
        for field in ["character", "scene", "prompt_pack", "caption", "notes"]:
            if not str(entry.get(field, "")).strip():
                errors.append(f"预览图清单 {file_name} 缺少字段：{field}")
        if entry.get("public_safe") is not True:
            errors.append(f"预览图必须标记 public_safe=true：{file_name}")
        prompt_pack = str(entry.get("prompt_pack", ""))
        if pack_ids and prompt_pack not in pack_ids:
            errors.append(f"预览图引用不存在的 Prompt Pack：{file_name} -> {prompt_pack}")

    for file_name in sorted(actual_files - manifest_files):
        errors.append(f"预览图未登记到 manifest：{file_name}")

    readme_path = ROOT / "README.md"
    if readme_path.exists():
        readme = readme_path.read_text(encoding="utf-8")
        targets = [m.group(1) for m in HTML_SRC_RE.finditer(readme)]
        targets.extend(m.group(1) for m in LOCAL_LINK_RE.finditer(readme))
        for raw in targets:
            target = clean_target(raw)
            if not target.startswith("预览图/"):
                continue
            file_name = Path(target).name
            if file_name not in manifest_files:
                errors.append(f"README 引用的预览图未登记到 manifest：{target}")


def check_preview_manifest_schema(manifest: dict, errors: list[str]) -> None:
    schema_ref = manifest.get("$schema")
    if not schema_ref:
        errors.append("预览图 manifest 缺少 $schema 引用")
        return
    schema_path = (ROOT / "预览图" / str(schema_ref)).resolve()
    try:
        schema_path.relative_to((ROOT / "预览图").resolve())
    except ValueError:
        errors.append(f"预览图 manifest $schema 不能指向预览图目录之外：{schema_ref}")
        return
    if not schema_path.exists():
        errors.append(f"预览图 manifest schema 文件不存在：预览图/{schema_ref}")
        return
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"预览图 manifest schema 无法读取：{exc}")
        return
    for key in ["$schema", "title", "type", "required", "properties", "$defs"]:
        if key not in schema:
            errors.append(f"预览图 manifest schema 缺少字段：{key}")
    for key in ["version", "description", "images"]:
        if key not in schema.get("properties", {}):
            errors.append(f"预览图 manifest schema.properties 缺少：{key}")


def check_prompt_pack_config(errors: list[str]) -> None:
    path = ROOT / "配置" / "prompt_packs.json"
    if not path.exists():
        return
    try:
        data = load_config(path)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Prompt Pack 配置无法读取：{exc}")
        return
    check_prompt_pack_schema(data, errors)
    for item in validate_config(data):
        errors.append(f"Prompt Pack 配置错误：{item}")
    for pack in data.get("packs", []):
        pack_id = pack.get("id")
        if not pack_id:
            continue
        rendered = render_pack(data, pack_id)
        for term in ["主体锁定", "安全约束", "防串约束", "非低俗", "不性感化", "不要混入"]:
            if term not in rendered:
                errors.append(f"Prompt Pack 输出缺少必要字段“{term}”：{pack_id}")


def check_prompt_pack_schema(data: dict, errors: list[str]) -> None:
    schema_ref = data.get("$schema")
    if not schema_ref:
        errors.append("Prompt Pack 配置缺少 $schema 引用")
        return
    schema_path = (ROOT / "配置" / str(schema_ref)).resolve()
    try:
        schema_path.relative_to((ROOT / "配置").resolve())
    except ValueError:
        errors.append(f"Prompt Pack $schema 不能指向配置目录之外：{schema_ref}")
        return
    if not schema_path.exists():
        errors.append(f"Prompt Pack $schema 文件不存在：配置/{schema_ref}")
        return
    try:
        import json

        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Prompt Pack schema 无法读取：{exc}")
        return
    for key in ["$schema", "title", "type", "required", "properties", "$defs"]:
        if key not in schema:
            errors.append(f"Prompt Pack schema 缺少字段：{key}")
    for key in ["characters", "templates", "packs", "global_quality_constraints"]:
        if key not in schema.get("properties", {}):
            errors.append(f"Prompt Pack schema.properties 缺少：{key}")


def check_generated_prompt_outputs(errors: list[str]) -> None:
    config_path = ROOT / "配置" / "prompt_packs.json"
    out_dir = ROOT / "生成提示词"
    if not config_path.exists() or not out_dir.exists():
        return
    try:
        data = load_config(config_path)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"无法校验自动生成提示词：{exc}")
        return

    index_path = out_dir / "README.md"
    expected_index = render_generated_index(data)
    if not index_path.exists():
        errors.append("缺少自动生成提示词索引：生成提示词/README.md")
    elif index_path.read_text(encoding="utf-8") != expected_index:
        errors.append("自动生成提示词索引已过期，请运行：python 工具/build_prompt_pack.py --all")

    matrix_path = out_dir / "覆盖矩阵.md"
    expected_matrix = render_coverage_matrix(data)
    if not matrix_path.exists():
        errors.append("缺少自动生成覆盖矩阵：生成提示词/覆盖矩阵.md")
    elif matrix_path.read_text(encoding="utf-8") != expected_matrix:
        errors.append("自动生成覆盖矩阵已过期，请运行：python 工具/build_prompt_pack.py --all")

    json_bundle_path = out_dir / GENERATED_JSON_BUNDLE
    expected_json_bundle = render_json_bundle(data)
    if not json_bundle_path.exists():
        errors.append(f"缺少自动生成 JSON bundle：生成提示词/{GENERATED_JSON_BUNDLE}")
    elif json_bundle_path.read_text(encoding="utf-8") != expected_json_bundle:
        errors.append(f"自动生成 JSON bundle 已过期：生成提示词/{GENERATED_JSON_BUNDLE}")
    else:
        check_generated_json_bundle_schema(json_bundle_path, errors)

    expected_files = {"README.md", "覆盖矩阵.md"}
    for pack in data.get("packs", []):
        pack_id = pack.get("id")
        if not pack_id:
            continue
        filename = generated_filename(pack_id)
        expected_files.add(filename)
        path = out_dir / filename
        expected = render_pack(data, pack_id, markdown=True)
        if not path.exists():
            errors.append(f"缺少自动生成提示词文件：生成提示词/{filename}")
        elif path.read_text(encoding="utf-8") != expected:
            errors.append(f"自动生成提示词文件已过期：生成提示词/{filename}")

    for path in out_dir.glob("*.md"):
        if path.name not in expected_files:
            errors.append(f"自动生成提示词目录存在多余 Markdown：生成提示词/{path.name}")

    expected_json_files = {GENERATED_JSON_BUNDLE, GENERATED_JSON_BUNDLE_SCHEMA}
    for path in out_dir.glob("*.json"):
        if path.name not in expected_json_files:
            errors.append(f"自动生成提示词目录存在多余 JSON：生成提示词/{path.name}")


def check_generated_json_bundle_schema(json_bundle_path: Path, errors: list[str]) -> None:
    try:
        bundle = json.loads(json_bundle_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"自动生成 JSON bundle 无法读取：{exc}")
        return
    schema_ref = bundle.get("$schema")
    if schema_ref != GENERATED_JSON_BUNDLE_SCHEMA:
        errors.append(f"自动生成 JSON bundle $schema 应为 {GENERATED_JSON_BUNDLE_SCHEMA}")
        return
    schema_path = json_bundle_path.parent / GENERATED_JSON_BUNDLE_SCHEMA
    if not schema_path.exists():
        errors.append(f"缺少自动生成 JSON bundle schema：生成提示词/{GENERATED_JSON_BUNDLE_SCHEMA}")
        return
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"自动生成 JSON bundle schema 无法读取：{exc}")
        return
    for key in ["$schema", "title", "type", "required", "properties", "$defs"]:
        if key not in schema:
            errors.append(f"自动生成 JSON bundle schema 缺少字段：{key}")
    for key in ["source_config", "version", "pack_count", "characters", "templates", "packs"]:
        if key not in schema.get("properties", {}):
            errors.append(f"自动生成 JSON bundle schema.properties 缺少：{key}")


def main() -> int:
    configure_stdout()
    errors: list[str] = []
    warnings: list[str] = []

    check_required_dirs(errors)
    check_required_files(errors)
    check_repo_style_config(errors)
    check_markdown_health(errors, warnings)
    check_local_links(errors)
    check_readme_badges(errors)
    check_secret_leaks(errors)
    check_content_safety_policy(errors)
    check_github_workflow(errors)
    check_role_safety(errors)
    check_reference_tracking(errors)
    check_preview_images(errors, warnings)
    check_prompt_pack_config(errors)
    check_generated_prompt_outputs(errors)

    print("# 提示词仓库质量检查")
    print()
    print(f"检查根目录：{ROOT}")
    print(f"错误：{len(errors)}")
    print(f"警告：{len(warnings)}")

    if errors:
        print("\n## Errors")
        for item in errors:
            print(f"- {item}")

    if warnings:
        print("\n## Warnings")
        for item in warnings:
            print(f"- {item}")

    if not errors:
        print("\nOK：结构、链接、README 徽章、仓库格式配置、忽略规则、密钥扫描、协作模板、内容安全政策、授权边界、角色安全约束、角色防串审计、预览图清单/schema、参考仓库追踪、Prompt Pack 配置/schema、统一质量门禁和自动导出文件通过。")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
