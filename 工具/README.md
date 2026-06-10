# 工具

这里放维护仓库用的小脚本。

## refresh_reference_summary.py

用途：读取三个参考仓库的 GitHub 基本信息，输出 Markdown 摘要。  
依赖：需要本机已安装并登录 `gh` CLI。

运行：

```powershell
python 工具/refresh_reference_summary.py
```

说明：

- 只抓仓库公开元信息和顶层目录。
- 不抓取或复制其他仓库的完整长提示词。
- 输出结果用于更新 `参考仓库/仓库追踪清单.md`。
- 已兼容 Windows 控制台 UTF-8 输出，避免仓库描述里有 emoji 时中断。

## check_prompt_repo.py

用途：检查仓库结构、Markdown 本地链接、README 预览图、角色安全约束和参考仓库追踪。  
不依赖网络，适合本地和 GitHub Actions 使用。

运行：

```powershell
python 工具/check_prompt_repo.py
```

如果输出 `OK`，说明当前仓库基础质量门禁通过。

## run_quality_gate.py

用途：统一运行本仓库的本地质量门禁，避免手动漏跑配置校验、仓库检查或单元测试。  
不依赖网络，GitHub Actions 也使用这个入口。

运行：

```powershell
python 工具/run_quality_gate.py
```

默认会依次执行：

```text
python 工具/build_prompt_pack.py --validate
python 工具/audit_character_prompts.py --check
python 工具/check_prompt_repo.py
python -m unittest discover -s tests -v
```

如果修改了 `配置/prompt_packs.json`，并且需要先刷新 `生成提示词/`：

```powershell
python 工具/run_quality_gate.py --refresh-generated
```

注意：CI 默认不使用 `--refresh-generated`，这样才能发现自动导出文件是否过期。

## audit_character_prompts.py

用途：根据 `配置/prompt_packs.json` 自动生成角色防串审计报告，检查三位角色的锚点、防串项、安全约束、芙宁娜污染源防护和多莉成年化/不儿童化约束。

生成报告：

```powershell
python 工具/audit_character_prompts.py
```

默认输出：

```text
评估/角色防串审计报告.md
```

检查报告是否过期：

```powershell
python 工具/audit_character_prompts.py --check
```

## build_prompt_pack.py

用途：读取 `配置/prompt_packs.json`，把角色锚点、输出类型、场景、构图、光线、材质、安全约束和防串约束组合成可复制提示词。  
不依赖网络，适合本地快速出 prompt。

查看可用组合：

```powershell
python 工具/build_prompt_pack.py --list
```

校验配置：

```powershell
python 工具/build_prompt_pack.py --validate
```

输出提示词：

```powershell
python 工具/build_prompt_pack.py furina_convention_phone
```

保存为 Markdown：

```powershell
python 工具/build_prompt_pack.py citlali_character_card --format markdown --out 示例/自动生成-茜特菈莉角色卡.md
```

批量导出全部 Prompt Pack：

```powershell
python 工具/build_prompt_pack.py --all
```

默认输出到：

```text
生成提示词/
```

同时会生成：

```text
生成提示词/覆盖矩阵.md
```

`生成提示词/README.md` 会自动生成「角色 × 用途」快速复制入口，`生成提示词/覆盖矩阵.md` 用于查看每个角色已经覆盖/缺失的输出类型。

`check_prompt_repo.py` 会检查这些导出文件是否和配置一致，如果过期需要重新运行 `--all`。

## 工具测试

运行：

```powershell
python 工具/run_quality_gate.py
```

统一质量门禁会覆盖 Prompt Pack 配置、角色防串审计、仓库结构、安全约束、自动导出文件和单元测试。单元测试本身会覆盖 Prompt Pack 渲染、批量导出、CLI、角色防串审计和统一质量门禁帮助入口。
