# 变更记录

## 2026-06-10

### Added

- 新增 `授权与使用边界.md`，说明原创模板、第三方 IP、预览图和商用场景边界。
- `工具/build_prompt_pack.py` 新增 `--format json`，可输出带角色、模板和 prompt 的机器可读记录。
- `工具/build_prompt_pack.py --all` 现在会导出 `生成提示词/prompt_packs.generated.json` 全量 JSON bundle。
- 新增 `生成提示词/prompt_packs.generated.schema.json`，并为全量 JSON bundle 增加 `$schema`。
- 全量 JSON bundle 新增 `source_config_sha256` 和 `generator` 元数据，方便外部工具核对来源配置与生成入口。
- 新增 `工具/run_quality_gate.py`，统一运行 Prompt Pack 校验、仓库质量检查和单元测试。
- 新增 `工具/lint_prompt_quality.py`、`评估/prompt_quality_rules.json` 和 `评估/Prompt文本质量审计报告.md`，用于生成前检查 Prompt 文本结构、安全、质量、模板意图、角色词和长度范围。
- 新增 `工具/validate_output_evaluations.py`、`评估/output_evaluations.example.json` 和 `评估/output_evaluations.schema.json`，用于结构化记录并校验出图评分。
- 新增 `工具/sync_preview_manifest.py`，可自动同步 README 预览图的宽高、比例和方向元数据。
- 新增 `工具/audit_character_prompts.py` 和 `评估/角色防串审计报告.md`，自动检查角色锚点、防串、安全约束和芙宁娜污染源防护。
- 新增 `预览图/README.md`、`预览图/manifest.json` 和 `预览图/manifest.schema.json`，记录公开预览图的角色、场景、Prompt Pack 和安全状态。
- 新增 `内容安全政策.md` 和 `SECURITY.md`，明确公开预览、Issue/PR 和 Prompt Pack 的安全规则。
- README 新增 CI、Prompt Pack、角色、模板、预览图数量和 JSON Schema 状态徽章。
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

- README 预览图数量徽章现在会跟随 `预览图/manifest.json` 自动校验，避免公开预览图数量过期。
- 预览图 manifest 现在记录真实 `width`、`height`、`aspect_ratio` 和 `orientation`，质量门禁会核对实际图片尺寸。
- 统一质量门禁现在会运行 `工具/sync_preview_manifest.py --check`，防止预览图尺寸元数据过期。
- 统一质量门禁现在会运行 `工具/lint_prompt_quality.py --check`，防止 Prompt 文本质量审计报告过期。
- 统一质量门禁现在会运行 `工具/validate_output_evaluations.py --check`，确保结构化出图评分示例有效。
- 质量门禁现在会检查授权与使用边界文件及 SECURITY 入口。
- 质量门禁新增轻量密钥扫描，检查常见 API key、GitHub token、AWS key 和高风险明文 secret。
- 扩展 `.gitignore`，并将 Python 缓存、虚拟环境、本地密钥和原始素材忽略规则纳入质量门禁。
- GitHub Actions 现在调用统一质量门禁入口 `python 工具/run_quality_gate.py`。
- 统一质量门禁现在会检查角色防串审计报告是否与 Prompt Pack 配置同步。
- 自动生成提示词索引现在包含「角色 × 用途」快速复制入口和命令行复制示例。
- 质量门禁现在会检查预览图 manifest/schema、README 引用、Prompt Pack 关联和 `public_safe=true`。
- README、贡献说明、工具说明和仓库质量门禁文档改为优先推荐统一质量门禁。
- 质量门禁现在会检查 GitHub Actions 工作流是否接入统一质量门禁。
- 根据 2026-06-10 联网复核的 OpenAI 图片生成资料，优化 `gpt-image-2` 模板结构，补充输出用途、主体锁定、文字策略、图像编辑保留项和参数建议。
- 更新固定室内漫展模板为分段自然语言版本，强化非低俗、真实材质和三角色防串约束。
- 同步优化 Prompt Pack 模板字段，并重新导出 15 个自动生成提示词。
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
