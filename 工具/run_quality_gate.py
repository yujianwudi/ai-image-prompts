from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


def run_step(label: str, command: list[str]) -> int:
    print(f"\n## {label}", flush=True)
    print("$ " + " ".join(command), flush=True)
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.stdout:
        print(result.stdout.rstrip(), flush=True)
    if result.returncode == 0:
        print(f"OK：{label}", flush=True)
    else:
        print(f"FAIL：{label}，退出码 {result.returncode}", flush=True)
    return result.returncode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run all local quality gates for the prompt repository.")
    parser.add_argument(
        "--refresh-generated",
        action="store_true",
        help="Regenerate 生成提示词/ plus generated audit reports before validation. Do not use this in CI; CI should catch stale exports.",
    )
    return parser.parse_args()


def main() -> int:
    configure_stdout()
    args = parse_args()
    python = sys.executable

    print("# 提示词仓库统一质量门禁", flush=True)
    print(f"检查根目录：{ROOT}", flush=True)

    steps: list[tuple[str, list[str]]] = []
    if args.refresh_generated:
        steps.append(("重新导出 Prompt Pack", [python, "工具/build_prompt_pack.py", "--all"]))
        steps.append(("重新生成角色防串审计报告", [python, "工具/audit_character_prompts.py"]))
        steps.append(("重新生成 Prompt 文本质量审计报告", [python, "工具/lint_prompt_quality.py"]))
        steps.append(("重新生成失败修正词库 Markdown", [python, "工具/validate_failure_fix_lexicon.py"]))
        steps.append(("重新生成出图评分汇总", [python, "工具/summarize_output_evaluations.py"]))
        steps.append(("重新生成失败修正建议", [python, "工具/suggest_failure_fixes.py"]))

    steps.extend(
        [
            ("校验 Prompt Pack 配置", [python, "工具/build_prompt_pack.py", "--validate"]),
            ("校验角色防串审计报告", [python, "工具/audit_character_prompts.py", "--check"]),
            ("校验 Prompt 文本质量审计报告", [python, "工具/lint_prompt_quality.py", "--check"]),
            ("校验失败修正词库", [python, "工具/validate_failure_fix_lexicon.py", "--check"]),
            ("校验结构化出图评分记录", [python, "工具/validate_output_evaluations.py", "--check"]),
            ("校验出图评分汇总", [python, "工具/summarize_output_evaluations.py", "--check"]),
            ("校验失败修正建议", [python, "工具/suggest_failure_fixes.py", "--check"]),
            ("校验预览图 manifest 尺寸元数据", [python, "工具/sync_preview_manifest.py", "--check"]),
            ("检查仓库结构与安全约束", [python, "工具/check_prompt_repo.py"]),
            ("运行单元测试", [python, "-m", "unittest", "discover", "-s", "tests", "-v"]),
        ]
    )

    for label, command in steps:
        code = run_step(label, command)
        if code != 0:
            return code

    print("\nOK：全部质量门禁通过。", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
