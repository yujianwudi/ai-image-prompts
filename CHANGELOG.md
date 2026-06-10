# 变更记录

## 2026-06-10

### Added

- 新增 `内容安全政策.md` 和 `SECURITY.md`，明确公开预览、Issue/PR 和 Prompt Pack 的安全规则。
- README 新增 CI、Prompt Pack、角色、模板和 JSON Schema 状态徽章。
- 新增 `.gitattributes` 和 `.editorconfig`，统一文本换行、编码和缩进规则。
- 新增 Pull Request 模板，提醒安全约束、Prompt Pack 导出和本地验证。
- 新增 GitHub Issue 模板：角色提示词、模板优化、出图问题反馈。
- 新增 `配置/prompt_packs.schema.json`，为 Prompt Pack 配置提供 JSON Schema。
- 补齐三位角色 × 五类输出类型的 Prompt Pack，共 15 个自动组合提示词。
- 新增 `生成提示词/覆盖矩阵.md`，展示角色与输出类型覆盖情况。
- 新增 `tests/test_prompt_pack_tools.py`，覆盖 Prompt Pack 配置、渲染、批量导出和 CLI。
- `工具/build_prompt_pack.py` 新增 `--all` 批量导出能力。
- 新增 `生成提示词/`，保存由 Prompt Pack 自动导出的可复制 Markdown 提示词。
- 新增 Prompt Pack 自动组合示例文档。
- 新增 `工具/build_prompt_pack.py`，支持列出、校验和输出可复制提示词。
- 新增 `配置/prompt_packs.json`，把角色锚点、模板字段和组合案例做成机器可读 Prompt Pack。
- 新增 GitHub Actions 工作流，push / pull request 时自动运行仓库质量检查。
- 新增 `工具/check_prompt_repo.py`，可本地检查仓库结构、链接、角色约束和参考仓库追踪。
- 新增仓库质量门禁文档，用于约束目录、链接、预览图和角色安全规则。
- 新增封面缩略图、长图教程/Slides、地图导览三类内容包装模板。
- 新增 Prompt as Code 字段化模板，用于固定任务类型、主体锁定、版式、文字策略和防串约束。
- 新增 `角色/` 与 `模板/` 两类目录结构。
- 新增 `示例/`、`评估/`、`预览图/` 交付目录。
- 新增 `参考仓库/` 和 `工具/`，用于持续追踪外部 awesome-gpt-image-2 仓库。
- 新增芙宁娜、茜特菈莉、朵莉亚/多莉角色提示词。
- 新增室内漫展、生活街拍、镜头、灯光、材质、动作、负面词等模板分类。
- 新增 OpenAI `gpt-image-2` 自然语言分段提示词指南。
- 新增商业海报、电商主图、信息图、UI截图、角色卡、分镜板模板。
- 新增 README 预览图。
- 新增可直接复制的完整示例提示词。
- 新增出图评分表、失败修正词库和迭代记录模板。
- 新增外部分类映射表、持续优化流程和仓库摘要刷新脚本。

### Changed

- 质量门禁现在会检查内容安全政策和 SECURITY 入口。
- 修正 README 模板数量徽章，并将 README 徽章计数纳入质量门禁。
- 质量门禁现在会检查仓库格式配置是否保留关键规则。
- 质量门禁现在会检查 GitHub Issue / PR 协作模板是否存在。
- 质量门禁和单元测试现在会检查 Prompt Pack `$schema` 引用。
- 覆盖矩阵现在显示三位角色已完整覆盖全部输出类型。
- 质量门禁和单元测试现在会检查覆盖矩阵是否与配置同步。
- `工具/build_prompt_pack.py --all` 现在会同时导出覆盖矩阵。
- 质量门禁现在要求 `tests/` 测试目录存在。
- GitHub Actions 现在同时运行仓库质量门禁和 Python 单元测试。
- 质量门禁现在会检查 `生成提示词/` 是否与 `配置/prompt_packs.json` 保持同步。
- 质量门禁现在会校验 Prompt Pack 配置引用和生成结果中的安全/防串字段。
- 补齐芙宁娜、茜特菈莉、多莉角色文件中的统一安全与防串约束。
- 修复参考仓库摘要脚本在 Windows GBK 控制台遇到 emoji 描述时报错的问题。
- 将原本的大模板文件拆分为分类文件，减少混淆。
- 将角色提示词和通用模板分开管理。
- 将负面词改写为更适合 gpt-image-2 的自然语言约束。
