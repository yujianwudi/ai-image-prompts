from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from build_prompt_pack import DEFAULT_CONFIG, load_config, render_pack

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "评估" / "角色防串审计报告.md"

REQUIRED_SAFETY_TERMS = ["非低俗", "不性感化"]
REQUIRED_RENDER_TERMS = ["主体锁定", "必须保留", "安全约束", "防串约束", "质量约束", "不要混入"]
REQUIRED_TEXT_TERMS = ["乱码"]
GLOBAL_REQUIRED_TERMS = ["不要混入", "不要水印", "不插画风"]
FURINA_CONTAMINATION_TERMS = ["芙宁娜", "白蓝短发", "蓝黑礼帽", "枫丹歌剧服"]
LOWBROW_TERMS = ["非低俗", "低俗", "不擦边", "擦边"]
SEXUALIZATION_TERMS = ["不性感化", "性感化"]


@dataclass(frozen=True)
class AuditResult:
    errors: list[str]
    warnings: list[str]
    character_rows: list[list[str]]
    template_rows: list[list[str]]
    pack_rows: list[list[str]]


def mark(ok: bool) -> str:
    return "OK" if ok else "FAIL"


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def contains_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def audit(data: dict[str, Any]) -> AuditResult:
    errors: list[str] = []
    warnings: list[str] = []
    character_rows: list[list[str]] = []
    template_rows: list[list[str]] = []
    pack_rows: list[list[str]] = []

    characters = data.get("characters", {})
    templates = data.get("templates", {})
    packs = data.get("packs", [])
    global_constraints = "\n".join(str(item) for item in data.get("global_quality_constraints", []))

    for term in GLOBAL_REQUIRED_TERMS:
        if term not in global_constraints:
            errors.append(f"全局质量约束缺少：{term}")

    for char_id, char in characters.items():
        anchor = str(char.get("anchor", ""))
        must_keep = [str(item) for item in char.get("must_keep", [])]
        avoid = [str(item) for item in char.get("avoid", [])]
        missing_keep = [item for item in must_keep if item not in anchor and item not in "\n".join(must_keep)]
        named_avoid = [item for item in avoid if contains_any(item, [other.get("display_name", "").split(" ")[0] for key, other in characters.items() if key != char_id])]
        avoid_text = "\n".join(avoid)
        has_safety = contains_any(avoid_text, LOWBROW_TERMS) and contains_any(avoid_text, SEXUALIZATION_TERMS)
        has_furina_guard = char_id == "furina" or contains_any("\n".join(avoid), FURINA_CONTAMINATION_TERMS)
        has_adult_guard = char_id != "dori" or contains_any(anchor + "\n".join(must_keep + avoid), ["成年", "不儿童化"])

        if len(must_keep) < 3:
            errors.append(f"{char_id} 的 must_keep 少于 3 个识别点")
        if len(avoid) < 2:
            errors.append(f"{char_id} 的 avoid 少于 2 个防串项")
        if missing_keep:
            warnings.append(f"{char_id} 的锚点未直接覆盖部分 must_keep：{', '.join(missing_keep)}")
        if not named_avoid:
            warnings.append(f"{char_id} 的 avoid 没有明确点名其他角色")
        if not has_safety:
            errors.append(f"{char_id} 的 avoid 缺少非低俗/不性感化约束")
        if not has_furina_guard:
            errors.append(f"{char_id} 缺少芙宁娜污染源防护")
        if not has_adult_guard:
            errors.append("dori 缺少成年化/不儿童化防护")

        character_rows.append(
            [
                char.get("display_name", char_id),
                str(len(must_keep)),
                str(len(avoid)),
                mark(has_safety),
                mark(has_furina_guard),
                mark(has_adult_guard),
            ]
        )

    for template_id, template in templates.items():
        safety = str(template.get("safety", ""))
        text_strategy = str(template.get("text_strategy", ""))
        has_safety = all(term in safety for term in REQUIRED_SAFETY_TERMS)
        has_text_guard = all(term in text_strategy for term in REQUIRED_TEXT_TERMS)
        if not has_safety:
            errors.append(f"{template_id} 的 safety 缺少非低俗/不性感化")
        if not has_text_guard:
            errors.append(f"{template_id} 的 text_strategy 缺少乱码约束")
        template_rows.append([template.get("task_type", template_id), mark(has_safety), mark(has_text_guard)])

    for pack in packs:
        pack_id = str(pack.get("id", ""))
        char_id = str(pack.get("character", ""))
        rendered = render_pack(data, pack_id)
        missing_sections = [term for term in REQUIRED_RENDER_TERMS if term not in rendered]
        missing_keep = [item for item in characters[char_id].get("must_keep", []) if str(item) not in rendered]
        has_furina_guard = char_id == "furina" or contains_any(rendered, FURINA_CONTAMINATION_TERMS)
        has_dori_adult_guard = char_id != "dori" or contains_any(rendered, ["成年", "不儿童化"])
        has_safety = all(term in rendered for term in REQUIRED_SAFETY_TERMS)

        if missing_sections:
            errors.append(f"{pack_id} 缺少输出段落：{', '.join(missing_sections)}")
        if missing_keep:
            errors.append(f"{pack_id} 缺少必须保留识别点：{', '.join(str(item) for item in missing_keep)}")
        if not has_furina_guard:
            errors.append(f"{pack_id} 缺少芙宁娜污染源防护")
        if not has_dori_adult_guard:
            errors.append(f"{pack_id} 缺少多莉成年化/不儿童化防护")
        if not has_safety:
            errors.append(f"{pack_id} 缺少非低俗/不性感化安全约束")

        pack_rows.append(
            [
                pack_id,
                characters[char_id].get("display_name", char_id),
                templates[pack.get("template", "")].get("task_type", pack.get("template", "")),
                mark(not missing_sections),
                mark(not missing_keep),
                mark(has_furina_guard),
                mark(has_safety and has_dori_adult_guard),
            ]
        )

    return AuditResult(errors, warnings, character_rows, template_rows, pack_rows)


def table(headers: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return lines


def render_report(data: dict[str, Any]) -> str:
    result = audit(data)
    status = "PASS" if not result.errors else "FAIL"
    lines: list[str] = [
        "# 角色防串审计报告",
        "",
        "这个报告由 `工具/audit_character_prompts.py` 根据 `配置/prompt_packs.json` 自动生成。",
        "如果修改角色或 Prompt Pack，请重新运行：",
        "",
        "```powershell",
        "python 工具/run_quality_gate.py --refresh-generated",
        "```",
        "",
        "## 总览",
        "",
        f"- 审计状态：{status}",
        f"- 错误：{len(result.errors)}",
        f"- 警告：{len(result.warnings)}",
        f"- 角色数：{len(data.get('characters', {}))}",
        f"- 模板数：{len(data.get('templates', {}))}",
        f"- Prompt Pack 数：{len(data.get('packs', []))}",
        "",
    ]

    if result.errors:
        lines.extend(["## 错误", ""])
        lines.extend(f"- {item}" for item in result.errors)
        lines.append("")
    if result.warnings:
        lines.extend(["## 警告", ""])
        lines.extend(f"- {item}" for item in result.warnings)
        lines.append("")

    lines.extend(["## 角色锚点与防串", ""])
    lines.extend(table(["角色", "必须保留数", "防串项数", "安全约束", "芙宁娜防护", "成年化防护"], result.character_rows))
    lines.extend(["", "## 模板安全与文字策略", ""])
    lines.extend(table(["输出类型", "非低俗/不性感化", "乱码约束"], result.template_rows))
    lines.extend(["", "## Prompt Pack 渲染检查", ""])
    lines.extend(
        table(
            ["Pack", "角色", "输出类型", "结构段落", "识别点", "芙宁娜防护", "安全/成人化"],
            result.pack_rows,
        )
    )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit character anti-contamination coverage.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to prompt_packs.json")
    parser.add_argument("--out", type=Path, default=DEFAULT_REPORT, help="Markdown report output path")
    parser.add_argument("--check", action="store_true", help="Fail if the report is missing or stale")
    return parser.parse_args()


def main() -> int:
    configure_stdout()
    args = parse_args()
    config_path = args.config if args.config.is_absolute() else ROOT / args.config
    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    data = load_config(config_path)
    report = render_report(data)
    result = audit(data)

    if args.check:
        if not out_path.exists():
            print(f"缺少角色防串审计报告：{out_path}")
            return 1
        current = out_path.read_text(encoding="utf-8")
        if current != report:
            print(f"角色防串审计报告已过期，请运行：python 工具/audit_character_prompts.py --out {out_path}")
            return 1
    else:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
        print(f"已写入角色防串审计报告：{out_path}")

    if result.errors:
        print("角色防串审计失败：")
        for item in result.errors:
            print(f"- {item}")
        return 1

    if result.warnings:
        print("角色防串审计警告：")
        for item in result.warnings:
            print(f"- {item}")

    print("OK：角色防串审计通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
