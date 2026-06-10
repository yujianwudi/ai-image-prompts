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
