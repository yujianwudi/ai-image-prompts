from __future__ import annotations

import json
import re
import struct
import sys
from math import gcd
from pathlib import Path
from urllib.parse import unquote

from build_prompt_pack import (
    GENERATED_API_REQUESTS_JSONL,
    GENERATED_API_REQUESTS_SCHEMA,
    GENERATED_CSV_INDEX,
    GENERATED_JSON_BUNDLE,
    GENERATED_JSON_BUNDLE_SCHEMA,
    GENERATED_TAG_COVERAGE_MATRIX,
    GENERATED_TAG_INDEX,
    generated_filename,
    load_config,
    render_coverage_matrix,
    render_csv_index,
    render_api_requests_jsonl,
    render_api_requests_schema,
    render_generated_index,
    render_json_bundle,
    render_tag_coverage_matrix,
    render_tag_index,
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
    "AGENTS.md",
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
    "模板/06-gpt-image-2官方规格自检清单.md",
    "模板/05-Prompt-as-Code字段模板.md",
    "模板/16-封面缩略图模板.md",
    "模板/17-长图教程Slides模板.md",
    "模板/18-地图导览模板.md",
    "示例/README.md",
    "评估/README.md",
    "评估/角色防串审计报告.md",
    "评估/Prompt文本质量审计报告.md",
    "评估/失败修正词库.md",
    "评估/prompt_quality_rules.json",
    "评估/prompt_quality_rules.schema.json",
    "评估/failure_fix_lexicon.json",
    "评估/failure_fix_lexicon.schema.json",
    "评估/output_evaluations.example.json",
    "评估/output_evaluations.schema.json",
    "评估/出图评分汇总.md",
    "评估/失败修正建议.md",
    "评估/项目仪表盘.md",
    "参考仓库/README.md",
    "参考仓库/仓库追踪清单.md",
    "参考仓库/分类映射表.md",
    "参考仓库/持续优化流程.md",
    "工具/README.md",
    "工具/refresh_reference_summary.py",
    "工具/audit_character_prompts.py",
    "工具/lint_prompt_quality.py",
    "工具/validate_failure_fix_lexicon.py",
    "工具/validate_output_evaluations.py",
    "工具/new_output_evaluation.py",
    "工具/summarize_output_evaluations.py",
    "工具/suggest_failure_fixes.py",
    "工具/build_project_dashboard.py",
    "工具/validate_gpt_image2_parameters.py",
    "工具/validate_api_requests.py",
    "工具/build_prompt_pack.py",
    "工具/sync_preview_manifest.py",
    "工具/run_quality_gate.py",
    "配置/README.md",
    "配置/prompt_packs.json",
    "配置/prompt_packs.schema.json",
    "配置/tag_taxonomy.json",
    "配置/tag_taxonomy.schema.json",
    "预览图/README.md",
    "预览图/manifest.json",
    "预览图/manifest.schema.json",
    "生成提示词/README.md",
    "生成提示词/prompt_packs.generated.schema.json",
    "生成提示词/prompt_packs.api_requests.jsonl",
    "生成提示词/prompt_packs.api_requests.schema.json",
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
HTML_IMG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
HTML_ATTR_RE = re.compile(r"([A-Za-z_:][\w:.-]*)\s*=\s*([\"'])(.*?)\2")
HTML_SRC_RE = re.compile(r"src=[\"']([^\"']+)[\"']")
C1_CONTROL_RE = re.compile(r"[\u0080-\u009f]")
TEXT_SCAN_SUFFIXES = {".md", ".py", ".json", ".jsonl", ".yml", ".yaml", ".txt", ".csv", ".ps1"}
TEXT_SCAN_NAMES = {".gitignore", ".gitattributes", ".editorconfig"}
IGNORED_TEXT_DIRS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".venv", "venv", "env", "tmp", "temp"}
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


def is_text_scan_file(path: Path) -> bool:
    if not path.is_file():
        return False
    if any(part in IGNORED_TEXT_DIRS for part in path.relative_to(ROOT).parts):
        return False
    return path.suffix.lower() in TEXT_SCAN_SUFFIXES or path.name in TEXT_SCAN_NAMES


def iter_text_scan_files() -> list[Path]:
    return [path for path in sorted(ROOT.rglob("*")) if is_text_scan_file(path)]


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


def html_tag_attrs(tag: str) -> dict[str, str]:
    return {match.group(1).lower(): match.group(3) for match in HTML_ATTR_RE.finditer(tag)}


def image_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        if len(data) < 24:
            raise ValueError("PNG 文件过短，无法读取尺寸")
        return struct.unpack(">II", data[16:24])
    if data.startswith(b"\xff\xd8"):
        return jpeg_dimensions(data)
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return webp_dimensions(data)
    raise ValueError("不支持的图片格式或无法读取尺寸")


def jpeg_dimensions(data: bytes) -> tuple[int, int]:
    sof_markers = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
    pos = 2
    while pos < len(data):
        while pos < len(data) and data[pos] != 0xFF:
            pos += 1
        while pos < len(data) and data[pos] == 0xFF:
            pos += 1
        if pos >= len(data):
            break
        marker = data[pos]
        pos += 1
        if marker in {0x01, 0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
            continue
        if pos + 2 > len(data):
            break
        segment_length = int.from_bytes(data[pos : pos + 2], "big")
        if segment_length < 2:
            break
        if marker in sof_markers:
            if pos + 7 > len(data):
                break
            height = int.from_bytes(data[pos + 3 : pos + 5], "big")
            width = int.from_bytes(data[pos + 5 : pos + 7], "big")
            return width, height
        pos += segment_length
    raise ValueError("JPEG 文件无法读取尺寸")


def webp_dimensions(data: bytes) -> tuple[int, int]:
    pos = 12
    while pos + 8 <= len(data):
        chunk_type = data[pos : pos + 4]
        chunk_size = int.from_bytes(data[pos + 4 : pos + 8], "little")
        payload = pos + 8
        if payload + chunk_size > len(data):
            break
        if chunk_type == b"VP8X" and chunk_size >= 10:
            width = int.from_bytes(data[payload + 4 : payload + 7], "little") + 1
            height = int.from_bytes(data[payload + 7 : payload + 10], "little") + 1
            return width, height
        if chunk_type == b"VP8L" and chunk_size >= 5 and data[payload] == 0x2F:
            bits = int.from_bytes(data[payload + 1 : payload + 5], "little")
            width = (bits & 0x3FFF) + 1
            height = ((bits >> 14) & 0x3FFF) + 1
            return width, height
        if chunk_type == b"VP8 " and chunk_size >= 10:
            frame = payload + 6
            if data[frame - 3 : frame] == b"\x9d\x01\x2a":
                width = int.from_bytes(data[frame : frame + 2], "little") & 0x3FFF
                height = int.from_bytes(data[frame + 2 : frame + 4], "little") & 0x3FFF
                return width, height
        pos = payload + chunk_size + (chunk_size % 2)
    raise ValueError("WebP 文件无法读取尺寸")


def reduced_aspect_ratio(width: int, height: int) -> str:
    common = gcd(width, height)
    return f"{width // common}:{height // common}"


def classify_orientation(width: int, height: int) -> str:
    if width > height:
        return "landscape"
    if width < height:
        return "portrait"
    return "square"


def check_readme_badges(errors: list[str]) -> None:
    readme_path = ROOT / "README.md"
    config_path = ROOT / "配置" / "prompt_packs.json"
    preview_manifest_path = ROOT / "预览图" / "manifest.json"
    if not readme_path.exists() or not config_path.exists():
        return
    readme = readme_path.read_text(encoding="utf-8")
    try:
        data = load_config(config_path)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"无法检查 README 徽章：{exc}")
        return
    try:
        preview_manifest = json.loads(preview_manifest_path.read_text(encoding="utf-8"))
        preview_entries = preview_manifest.get("images", [])
    except Exception as exc:  # noqa: BLE001
        errors.append(f"无法检查 README 预览图徽章：{exc}")
        return
    if not isinstance(preview_entries, list):
        errors.append("无法检查 README 预览图徽章：manifest.images 不是 array")
        return
    preview_count = len(preview_entries)
    template_count = len([path for path in (ROOT / "模板").glob("*.md") if path.name.lower() != "readme.md"])
    expected = {
        "CI badge": "actions/workflows/validate.yml/badge.svg",
        "Prompt Packs badge": f"Prompt%20Packs-{len(data.get('packs', []))}-",
        "Characters badge": f"Characters-{len(data.get('characters', {}))}-",
        "Templates badge": f"Templates-{template_count}-",
        "Preview Images badge": f"Preview%20Images-{preview_count}-",
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


def check_text_file_hygiene(errors: list[str]) -> None:
    for path in iter_text_scan_files():
        data = path.read_bytes()
        if data.startswith(b"\xef\xbb\xbf"):
            errors.append(f"文本文件不应包含 UTF-8 BOM：{rel(path)}")
        if b"\r\n" in data or b"\r" in data:
            errors.append(f"文本文件必须使用 LF 换行：{rel(path)}")
        if data and not data.endswith(b"\n"):
            errors.append(f"文本文件末尾必须保留换行：{rel(path)}")


def find_unclosed_markdown_fence(text: str) -> tuple[int, str] | None:
    in_fence = False
    fence_char = ""
    fence_len = 0
    start_line = 0
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.lstrip(" ")
        indent = len(line) - len(stripped)
        if indent > 3 or not (stripped.startswith("```") or stripped.startswith("~~~")):
            continue
        current_char = stripped[0]
        current_len = len(stripped) - len(stripped.lstrip(current_char))
        if current_len < 3:
            continue
        rest = stripped[current_len:].strip()
        if not in_fence:
            in_fence = True
            fence_char = current_char
            fence_len = current_len
            start_line = line_number
        elif current_char == fence_char and current_len >= fence_len and not rest:
            in_fence = False
            fence_char = ""
            fence_len = 0
            start_line = 0
    if in_fence:
        return start_line, fence_char * fence_len
    return None


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
        unclosed_fence = find_unclosed_markdown_fence(text)
        if unclosed_fence:
            start_line, fence = unclosed_fence
            errors.append(f"Markdown 代码块未闭合：{rel(path)}:{start_line} ({fence})")
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
    for path in iter_text_scan_files():
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


def check_agent_guidance(errors: list[str]) -> None:
    path = ROOT / "AGENTS.md"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    required_terms = [
        "python 工具/run_quality_gate.py",
        "--refresh-generated",
        "不要手工编辑",
        "生成提示词/",
        "gpt-image-2",
        "1024x1824",
        "validate_gpt_image2_parameters.py",
        "new_output_evaluation.py",
        "tag_taxonomy.json",
        "非低俗",
        "不性感化",
        "不要添加正式 `LICENSE` 文件",
        "不要把 Midjourney 参数写进 OpenAI API 参数",
        "不要把 token、临时脚本或密钥提交进仓库",
    ]
    for term in required_terms:
        if term not in text:
            errors.append(f"AGENTS.md 缺少维护指引：{term}")


def check_github_workflow(errors: list[str]) -> None:
    path = ROOT / ".github" / "workflows" / "validate.yml"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    if "工具/run_quality_gate.py" not in text:
        errors.append("GitHub Actions 应调用统一质量门禁：python 工具/run_quality_gate.py")
    required_terms = {
        "actions/checkout@v6": "GitHub Actions 应使用 Node 24 版本的 actions/checkout@v6",
        "actions/setup-python@v6": "GitHub Actions 应使用 Node 24 版本的 actions/setup-python@v6",
        "permissions:\n  contents: read": "GitHub Actions 应显式限制 contents: read 最小权限",
        "timeout-minutes: 10": "GitHub Actions check job 应设置 10 分钟超时",
    }
    for term, message in required_terms.items():
        if term not in text:
            errors.append(message)


def check_unified_quality_gate(errors: list[str]) -> None:
    path = ROOT / "工具" / "run_quality_gate.py"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    required_terms = {
        '"compileall", "-q", "工具", "tests"': "统一质量门禁应编译 工具/ 和 tests/ 下的 Python 源码",
        '"unittest", "discover", "-s", "tests", "-v"': "统一质量门禁应继续运行 unittest",
    }
    for term, message in required_terms.items():
        if term not in text:
            errors.append(message)


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
    manifest_file_order: list[str] = []
    manifest_captions: dict[str, str] = {}
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
        if file_name in manifest_files:
            errors.append(f"预览图清单 file 重复：{file_name}")
        manifest_files.add(file_name)
        manifest_file_order.append(file_name)
        if "/" in file_name or "\\" in file_name:
            errors.append(f"预览图清单 file 只能是文件名：{file_name}")
        if file_name not in actual_files:
            errors.append(f"预览图清单引用不存在的图片：{file_name}")
        else:
            image_path = preview_dir / file_name
            try:
                width, height = image_dimensions(image_path)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"预览图无法读取尺寸：{file_name} -> {exc}")
            else:
                expected_metadata = {
                    "width": width,
                    "height": height,
                    "aspect_ratio": reduced_aspect_ratio(width, height),
                    "orientation": classify_orientation(width, height),
                }
                for field, expected in expected_metadata.items():
                    if entry.get(field) != expected:
                        errors.append(f"预览图清单 {file_name} 的 {field} 应为 {expected}")
        for field in ["character", "scene", "prompt_pack", "caption", "notes"]:
            if not str(entry.get(field, "")).strip():
                errors.append(f"预览图清单 {file_name} 缺少字段：{field}")
        caption = str(entry.get("caption", "")).strip()
        if caption:
            manifest_captions[file_name] = caption
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
        readme_preview_imgs: set[str] = set()
        readme_preview_order: list[str] = []
        for match in HTML_IMG_RE.finditer(readme):
            attrs = html_tag_attrs(match.group(0))
            target = clean_target(attrs.get("src", ""))
            if not target.startswith("预览图/"):
                continue
            file_name = Path(target).name
            if file_name in readme_preview_imgs:
                errors.append(f"README 预览图重复展示：{target}")
            readme_preview_imgs.add(file_name)
            readme_preview_order.append(file_name)
            if file_name not in manifest_files:
                errors.append(f"README 引用的预览图未登记到 manifest：{target}")
                continue
            alt = attrs.get("alt", "").strip()
            expected_caption = manifest_captions.get(file_name, "")
            if not alt:
                errors.append(f"README 预览图缺少 alt：{target}")
            elif expected_caption and alt != expected_caption:
                errors.append(f"README 预览图 alt 与 manifest caption 不一致：{target} -> 应为 {expected_caption}")

        targets = [m.group(1) for m in HTML_SRC_RE.finditer(readme)]
        targets.extend(m.group(1) for m in LOCAL_LINK_RE.finditer(readme))
        for raw in targets:
            target = clean_target(raw)
            if not target.startswith("预览图/"):
                continue
            file_name = Path(target).name
            if file_name not in manifest_files:
                errors.append(f"README 引用的预览图未登记到 manifest：{target}")
        for file_name, caption in manifest_captions.items():
            if file_name not in readme_preview_imgs:
                errors.append(f"README 缺少预览图展示：预览图/{file_name}")
            if f"<sub>{caption}</sub>" not in readme:
                errors.append(f"README 预览图缺少 manifest caption 展示：预览图/{file_name} -> {caption}")
        if readme_preview_order and set(readme_preview_order) == set(manifest_file_order):
            if readme_preview_order != manifest_file_order:
                errors.append(
                    "README 预览图展示顺序应与 manifest.images 一致："
                    f"当前 {', '.join(readme_preview_order)}；应为 {', '.join(manifest_file_order)}"
                )


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
    preview_props = schema.get("$defs", {}).get("preview_image", {}).get("properties", {})
    for key in ["width", "height", "aspect_ratio", "orientation"]:
        if key not in preview_props:
            errors.append(f"预览图 manifest schema.preview_image.properties 缺少：{key}")
    preview_required = set(schema.get("$defs", {}).get("preview_image", {}).get("required", []))
    for key in ["width", "height", "aspect_ratio", "orientation"]:
        if key not in preview_required:
            errors.append(f"预览图 manifest schema.preview_image.required 缺少：{key}")


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
    for key in ["characters", "templates"]:
        property_names = schema.get("properties", {}).get(key, {}).get("propertyNames", {})
        if property_names.get("pattern") != "^[a-z0-9_]+$":
            errors.append(f"Prompt Pack schema.properties.{key}.propertyNames.pattern 应限制为小写 slug")
    template_props = schema.get("$defs", {}).get("template", {}).get("properties", {})
    if "tags" not in template_props:
        errors.append("Prompt Pack schema.template.properties 缺少：tags")


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

    tag_index_path = out_dir / GENERATED_TAG_INDEX
    expected_tag_index = render_tag_index(data)
    if not tag_index_path.exists():
        errors.append(f"缺少自动生成标签索引：生成提示词/{GENERATED_TAG_INDEX}")
    elif tag_index_path.read_text(encoding="utf-8") != expected_tag_index:
        errors.append(f"自动生成标签索引已过期：生成提示词/{GENERATED_TAG_INDEX}")

    tag_coverage_path = out_dir / GENERATED_TAG_COVERAGE_MATRIX
    expected_tag_coverage = render_tag_coverage_matrix(data)
    if not tag_coverage_path.exists():
        errors.append(f"缺少自动生成标签覆盖矩阵：生成提示词/{GENERATED_TAG_COVERAGE_MATRIX}")
    elif tag_coverage_path.read_text(encoding="utf-8") != expected_tag_coverage:
        errors.append(f"自动生成标签覆盖矩阵已过期：生成提示词/{GENERATED_TAG_COVERAGE_MATRIX}")

    json_bundle_path = out_dir / GENERATED_JSON_BUNDLE
    expected_json_bundle = render_json_bundle(data)
    if not json_bundle_path.exists():
        errors.append(f"缺少自动生成 JSON bundle：生成提示词/{GENERATED_JSON_BUNDLE}")
    elif json_bundle_path.read_text(encoding="utf-8") != expected_json_bundle:
        errors.append(f"自动生成 JSON bundle 已过期：生成提示词/{GENERATED_JSON_BUNDLE}")
    else:
        check_generated_json_bundle_schema(json_bundle_path, errors)

    api_requests_path = out_dir / GENERATED_API_REQUESTS_JSONL
    expected_api_requests = render_api_requests_jsonl(data)
    if not api_requests_path.exists():
        errors.append(f"缺少自动生成 API 请求 JSONL：生成提示词/{GENERATED_API_REQUESTS_JSONL}")
    elif api_requests_path.read_text(encoding="utf-8") != expected_api_requests:
        errors.append(f"自动生成 API 请求 JSONL 已过期：生成提示词/{GENERATED_API_REQUESTS_JSONL}")
    else:
        check_generated_api_requests_jsonl(api_requests_path, data, errors)

    api_requests_schema_path = out_dir / GENERATED_API_REQUESTS_SCHEMA
    expected_api_requests_schema = render_api_requests_schema()
    if not api_requests_schema_path.exists():
        errors.append(f"缺少自动生成 API 请求 JSONL schema：生成提示词/{GENERATED_API_REQUESTS_SCHEMA}")
    elif api_requests_schema_path.read_text(encoding="utf-8") != expected_api_requests_schema:
        errors.append(f"自动生成 API 请求 JSONL schema 已过期：生成提示词/{GENERATED_API_REQUESTS_SCHEMA}")

    csv_index_path = out_dir / GENERATED_CSV_INDEX
    expected_csv_index = render_csv_index(data)
    if not csv_index_path.exists():
        errors.append(f"缺少自动生成 CSV 索引：生成提示词/{GENERATED_CSV_INDEX}")
    elif csv_index_path.read_text(encoding="utf-8") != expected_csv_index:
        errors.append(f"自动生成 CSV 索引已过期：生成提示词/{GENERATED_CSV_INDEX}")

    expected_files = {"README.md", "覆盖矩阵.md", GENERATED_TAG_INDEX, GENERATED_TAG_COVERAGE_MATRIX}
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

    expected_json_files = {GENERATED_JSON_BUNDLE, GENERATED_JSON_BUNDLE_SCHEMA, GENERATED_API_REQUESTS_SCHEMA}
    for path in out_dir.glob("*.json"):
        if path.name not in expected_json_files:
            errors.append(f"自动生成提示词目录存在多余 JSON：生成提示词/{path.name}")

    expected_jsonl_files = {GENERATED_API_REQUESTS_JSONL}
    for path in out_dir.glob("*.jsonl"):
        if path.name not in expected_jsonl_files:
            errors.append(f"自动生成提示词目录存在多余 JSONL：生成提示词/{path.name}")

    expected_csv_files = {GENERATED_CSV_INDEX}
    for path in out_dir.glob("*.csv"):
        if path.name not in expected_csv_files:
            errors.append(f"自动生成提示词目录存在多余 CSV：生成提示词/{path.name}")


def check_generated_api_requests_jsonl(api_requests_path: Path, data: dict[str, object], errors: list[str]) -> None:
    try:
        records = [json.loads(line) for line in api_requests_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except Exception as exc:  # noqa: BLE001
        errors.append(f"自动生成 API 请求 JSONL 无法读取：{exc}")
        return
    expected_ids = [str(pack.get("id", "")) for pack in data.get("packs", []) if isinstance(pack, dict)]
    record_ids = [str(record.get("id", "")) for record in records if isinstance(record, dict)]
    if record_ids != expected_ids:
        errors.append("自动生成 API 请求 JSONL 的记录顺序或数量与 Prompt Pack 不一致")
    for record in records:
        if not isinstance(record, dict):
            errors.append("自动生成 API 请求 JSONL 包含非 object 行")
            continue
        request = record.get("request")
        if not isinstance(request, dict):
            errors.append(f"API 请求 JSONL 记录缺少 request：{record.get('id')}")
            continue
        for key in ["model", "prompt", "size", "quality", "output_format", "background"]:
            if key not in request:
                errors.append(f"API 请求 JSONL 记录 {record.get('id')} 缺少 request.{key}")
        if request.get("model") != "gpt-image-2":
            errors.append(f"API 请求 JSONL 记录 {record.get('id')} 的 model 不是 gpt-image-2")
        if not str(request.get("prompt", "")).strip():
            errors.append(f"API 请求 JSONL 记录 {record.get('id')} 的 prompt 为空")


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
    generated_required = [
        "source_config",
        "source_config_sha256",
        "generator",
        "version",
        "pack_count",
        "characters",
        "templates",
        "packs",
    ]
    schema_required = set(schema.get("required", []))
    for key in generated_required:
        if key not in schema_required:
            errors.append(f"自动生成 JSON bundle schema.required 缺少：{key}")
    for key in generated_required:
        if key not in schema.get("properties", {}):
            errors.append(f"自动生成 JSON bundle schema.properties 缺少：{key}")
    pack_props = schema.get("$defs", {}).get("generated_pack", {}).get("properties", {})
    if "tags" not in pack_props:
        errors.append("自动生成 JSON bundle schema.generated_pack.properties 缺少：tags")
    pack_required = set(schema.get("$defs", {}).get("generated_pack", {}).get("required", []))
    if "tags" not in pack_required:
        errors.append("自动生成 JSON bundle schema.generated_pack.required 缺少：tags")
    template_props = schema.get("$defs", {}).get("generated_template_ref", {}).get("properties", {})
    if "tags" not in template_props:
        errors.append("自动生成 JSON bundle schema.generated_template_ref.properties 缺少：tags")


def main() -> int:
    configure_stdout()
    errors: list[str] = []
    warnings: list[str] = []

    check_required_dirs(errors)
    check_required_files(errors)
    check_repo_style_config(errors)
    check_text_file_hygiene(errors)
    check_markdown_health(errors, warnings)
    check_local_links(errors)
    check_readme_badges(errors)
    check_secret_leaks(errors)
    check_content_safety_policy(errors)
    check_agent_guidance(errors)
    check_github_workflow(errors)
    check_unified_quality_gate(errors)
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
        print("\nOK：结构、链接、README 徽章、仓库格式配置、文本文件卫生、忽略规则、密钥扫描、协作模板、内容安全政策、授权边界、角色安全约束、角色防串审计、Prompt 文本质量审计、失败修正词库、结构化出图评分日期/图片路径/failure_ids 去重/汇总、评分骨架工具、失败修正建议、项目仪表盘、gpt-image-2 参数自检、预览图清单/schema/尺寸方向、README 预览图 alt/caption/顺序、参考仓库追踪、Prompt Pack 配置/schema/ID slug、标签 taxonomy、标签覆盖矩阵、API 请求 JSONL、Python 源码编译、统一质量门禁和自动导出文件通过。")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
