from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass


SIZE_RE = re.compile(r"^(?P<width>\d+)x(?P<height>\d+)$")

MIN_SIDE = 512
MAX_SIDE = 3840
MIN_PIXELS = 655_360
MAX_PIXELS = 8_294_400
GRID = 16
MIN_ASPECT = 1 / 3
MAX_ASPECT = 3
TARGET_9_16 = 9 / 16
ASPECT_TOLERANCE = 0.01


@dataclass(frozen=True)
class SizeProfile:
    name: str
    size: str
    quality: str
    use_case: str

    @property
    def width(self) -> int:
        return parse_size_spec(self.size)[0]

    @property
    def height(self) -> int:
        return parse_size_spec(self.size)[1]


RECOMMENDED_PROFILES: tuple[SizeProfile, ...] = (
    SizeProfile("draft_phone", "640x1136", "low", "草稿：先看角色锚点、防串和构图"),
    SizeProfile("fast_phone", "720x1280", "low", "快速严格 9:16 手机竖图"),
    SizeProfile("standard_phone", "864x1536", "medium", "常规公开预览与角色图"),
    SizeProfile("repo_default", "1024x1824", "medium", "本仓库默认写实漫展手机竖图"),
    SizeProfile("detail_preview", "1088x1936", "high", "细节更密的角色卡、封面或海报预览"),
    SizeProfile("upper_stable", "1440x2560", "high", "高细节竖版交付上限档，先用低档确认不串角色"),
    SizeProfile("max_experimental", "2160x3840", "high", "接近最大 4K 竖图，成本高且更适合最后放大"),
)


@dataclass(frozen=True)
class SizeValidation:
    width: int
    height: int
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def pixels(self) -> int:
        return self.width * self.height

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height

    @property
    def is_valid(self) -> bool:
        return not self.errors

    @property
    def is_near_9_16(self) -> bool:
        return is_near_9_16(self.width, self.height)


def parse_size_spec(size: str) -> tuple[int, int]:
    match = SIZE_RE.fullmatch(size.strip().lower())
    if not match:
        raise ValueError(f"size 必须写成 WIDTHxHEIGHT，例如 1024x1824：{size!r}")
    return int(match.group("width")), int(match.group("height"))


def is_near_9_16(width: int, height: int, tolerance: float = ASPECT_TOLERANCE) -> bool:
    if height <= 0:
        return False
    ratio = width / height
    return abs(ratio - TARGET_9_16) / TARGET_9_16 <= tolerance


def validate_dimensions(width: int, height: int, *, require_9_16: bool = False) -> SizeValidation:
    errors: list[str] = []
    warnings: list[str] = []

    for label, value in (("width", width), ("height", height)):
        if value < MIN_SIDE:
            errors.append(f"{label} 小于 {MIN_SIDE}")
        if value > MAX_SIDE:
            errors.append(f"{label} 大于 {MAX_SIDE}")
        if value % GRID != 0:
            errors.append(f"{label} 不是 {GRID} 的倍数")

    pixels = width * height
    if pixels < MIN_PIXELS:
        errors.append(f"总像素 {pixels} 小于 {MIN_PIXELS}")
    if pixels > MAX_PIXELS:
        errors.append(f"总像素 {pixels} 大于 {MAX_PIXELS}")

    ratio = width / height
    if ratio < MIN_ASPECT or ratio > MAX_ASPECT:
        errors.append("宽高比不在 1:3 到 3:1 范围内")

    if width >= height:
        warnings.append("这不是竖图尺寸")
    if require_9_16 and not is_near_9_16(width, height):
        warnings.append("这不是接近 9:16 的竖图尺寸；1024x1536 属于 2:3 备选，不要标成严格 9:16")

    return SizeValidation(width=width, height=height, errors=tuple(errors), warnings=tuple(warnings))


def validate_size_spec(size: str, *, require_9_16: bool = False) -> SizeValidation:
    width, height = parse_size_spec(size)
    return validate_dimensions(width, height, require_9_16=require_9_16)


def render_markdown() -> str:
    lines = [
        "# gpt-image-2 推荐尺寸档位自检",
        "",
        "这些档位遵守本仓库记录的 OpenAI `gpt-image-2` 尺寸约束：边长 512-3840、宽高均为 16 的倍数、总像素 655,360-8,294,400、宽高比在 1:3 到 3:1 之间。",
        "",
        "| 档位 | size | quality | 接近 9:16 | 用途 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for profile in RECOMMENDED_PROFILES:
        validation = validate_size_spec(profile.size, require_9_16=True)
        status = "是" if validation.is_valid and validation.is_near_9_16 else "否"
        lines.append(f"| `{profile.name}` | `{profile.size}` | `{profile.quality}` | {status} | {profile.use_case} |")
    lines.extend(
        [
            "",
            "提示：`1024x1536` 是 API 可用的 2:3 竖图备选，但不是严格 9:16；如果目标是手机竖屏展示，优先使用上表档位。",
            "",
        ]
    )
    return "\n".join(lines)


def format_validation(size: str, validation: SizeValidation) -> str:
    status = "OK" if validation.is_valid else "ERROR"
    parts = [
        f"{status} {size}",
        f"pixels={validation.pixels}",
        f"aspect={validation.width}:{validation.height}",
        f"near_9_16={'yes' if validation.is_near_9_16 else 'no'}",
    ]
    if validation.errors:
        parts.append("errors=" + "; ".join(validation.errors))
    if validation.warnings:
        parts.append("warnings=" + "; ".join(validation.warnings))
    return " | ".join(parts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate OpenAI gpt-image-2 size profiles used by this prompt repository.")
    parser.add_argument("--size", action="append", help="Validate a size such as 1024x1824. Can be used multiple times.")
    parser.add_argument("--require-9-16", action="store_true", help="Warn when a valid API size is not close to 9:16.")
    parser.add_argument("--list", action="store_true", help="List the repository's recommended gpt-image-2 size profiles.")
    parser.add_argument("--markdown", action="store_true", help="Print the recommended profiles as Markdown.")
    parser.add_argument("--check", action="store_true", help="Check that all recommended profiles are valid and close to 9:16.")
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()

    if args.markdown:
        print(render_markdown())
        return 0

    if args.list:
        for profile in RECOMMENDED_PROFILES:
            print(f"{profile.name}: size={profile.size}, quality={profile.quality}, use_case={profile.use_case}")
        return 0

    sizes = args.size or []
    if args.check:
        sizes.extend(profile.size for profile in RECOMMENDED_PROFILES)

    if not sizes:
        print(render_markdown())
        return 0

    failed = False
    warned = False
    for size in sizes:
        validation = validate_size_spec(size, require_9_16=args.require_9_16 or args.check)
        print(format_validation(size, validation))
        failed = failed or not validation.is_valid
        warned = warned or bool(validation.warnings)

    if args.check and (failed or warned):
        return 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
