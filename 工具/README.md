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
