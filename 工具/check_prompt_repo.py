from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

from build_prompt_pack import load_config, render_pack, validate_config

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
]

REQUIRED_FILES = [
    "README.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "免责声明.md",
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
    "参考仓库/README.md",
    "参考仓库/仓库追踪清单.md",
    "参考仓库/分类映射表.md",
    "参考仓库/持续优化流程.md",
    "工具/README.md",
    "工具/refresh_reference_summary.py",
    "工具/build_prompt_pack.py",
    "配置/README.md",
    "配置/prompt_packs.json",
]

REFERENCE_REPOS = [
    "EvoLinkAI/awesome-gpt-image-2-API-and-Prompts",
    "freestylefly/awesome-gpt-image-2",
    "YouMind-OpenLab/awesome-gpt-image-2",
]

LOCAL_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
HTML_SRC_RE = re.compile(r"src=[\"']([^\"']+)[\"']")
C1_CONTROL_RE = re.compile(r"[\u0080-\u009f]")


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


def check_prompt_pack_config(errors: list[str]) -> None:
    path = ROOT / "配置" / "prompt_packs.json"
    if not path.exists():
        return
    try:
        data = load_config(path)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Prompt Pack 配置无法读取：{exc}")
        return
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


def main() -> int:
    configure_stdout()
    errors: list[str] = []
    warnings: list[str] = []

    check_required_dirs(errors)
    check_required_files(errors)
    check_markdown_health(errors, warnings)
    check_local_links(errors)
    check_role_safety(errors)
    check_reference_tracking(errors)
    check_preview_images(errors, warnings)
    check_prompt_pack_config(errors)

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
        print("\nOK：结构、链接、角色安全约束、参考仓库追踪和 Prompt Pack 配置通过。")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
