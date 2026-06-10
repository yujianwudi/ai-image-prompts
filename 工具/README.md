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

用途：检查仓库结构、AGENTS 维护指引、Markdown 本地链接、README 预览图 alt/caption/顺序、预览图 manifest schema/结构/尺寸/方向、角色安全约束和参考仓库追踪。
不依赖网络，适合本地和 GitHub Actions 使用。

运行：

```powershell
python 工具/check_prompt_repo.py
```

如果输出 `OK`，说明当前仓库基础质量门禁通过。

## sync_preview_manifest.py

用途：读取 `预览图/manifest.json` 和实际图片文件，先校验未知字段、空白文案、重复图片、Prompt Pack 引用和 `public_safe` 状态，再自动同步 `width`、`height`、`aspect_ratio` 和 `orientation`。
不依赖网络，适合新增、替换或压缩 README 预览图后运行。

同步 manifest：

```powershell
python 工具/sync_preview_manifest.py
```

只检查是否过期：

```powershell
python 工具/sync_preview_manifest.py --check
```

## run_quality_gate.py

用途：统一运行本仓库的本地质量门禁，避免手动漏跑配置校验、仓库检查、Python 源码编译或单元测试。
不依赖网络，GitHub Actions 也使用这个入口。

运行：

```powershell
python 工具/run_quality_gate.py
```

默认会依次执行：

```text
python 工具/build_prompt_pack.py --validate
python 工具/audit_character_prompts.py --check
python 工具/lint_prompt_quality.py --check
python 工具/validate_failure_fix_lexicon.py --check
python 工具/validate_output_evaluations.py --check
python 工具/summarize_output_evaluations.py --check
python 工具/suggest_failure_fixes.py --check
python 工具/build_project_dashboard.py --check
python 工具/validate_gpt_image2_parameters.py --check
python 工具/sync_preview_manifest.py --check
python 工具/check_prompt_repo.py
python -m compileall -q 工具 tests
python -m unittest discover -s tests -v
```

如果修改了 `配置/prompt_packs.json`，并且需要先刷新 `生成提示词/`：

```powershell
python 工具/run_quality_gate.py --refresh-generated
```

注意：CI 默认不使用 `--refresh-generated`，这样才能发现自动导出文件是否过期。

## validate_failure_fix_lexicon.py

用途：校验 `评估/failure_fix_lexicon.json`，并用它生成可读版 `评估/失败修正词库.md`。用于把常见失败类型、识别线索、修正词和下一步动作结构化，并拦截未知字段、空白文本、非法 applies_to 和重复 applies_to / detect_terms / must_include。

生成 Markdown：

```powershell
python 工具/validate_failure_fix_lexicon.py
```

只检查 JSON 和 Markdown 是否同步：

```powershell
python 工具/validate_failure_fix_lexicon.py --check
```

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

## lint_prompt_quality.py

用途：根据 `配置/prompt_packs.json` 和 `评估/prompt_quality_rules.json` 自动检查渲染后的 Prompt Pack 文本质量，覆盖结构段落、安全词、质量词、模板意图词、角色识别点、长度范围和禁用平台参数泄漏；规则文件本身也会拦截未知字段、空白字符串和重复词条。

生成报告：

```powershell
python 工具/lint_prompt_quality.py
```

默认输出：

```text
评估/Prompt文本质量审计报告.md
```

检查报告是否过期：

```powershell
python 工具/lint_prompt_quality.py --check
```

## validate_output_evaluations.py

用途：校验结构化出图评分记录，检查记录 ID 是否为小写 slug、是否混入未知字段、version / description / issues / next_action / notes 是否包含非空白字符、评分日期是否是真实日历日期、评分总分、Prompt Pack/角色引用、图片路径存在且为 jpg/jpeg/png/webp、公开安全状态、decision 和 failure_ids 去重。

默认校验示例文件：

```powershell
python 工具/validate_output_evaluations.py --check
```

校验自定义评分记录：

```powershell
python 工具/validate_output_evaluations.py --file 评估/my_output_evaluations.json --check
```

## new_output_evaluation.py

用途：根据 Prompt Pack 和图片路径生成一条结构化出图评分记录骨架，并在输出前复用结构化评分校验器，减少手写 JSON 漏字段、图片路径填成非图片、写错角色、写错或重复填写 `failure_ids` 的概率。

查看可用失败类型：

```powershell
python 工具/new_output_evaluation.py --list-failures
```

生成完整 JSON 文档：

```powershell
python 工具/new_output_evaluation.py `
  --prompt-pack furina_readme_preview `
  --image-file 预览图/furina-dessert-01.jpg `
  --id preview-furina-dessert-new `
  --failure-id composition_ratio_mismatch `
  --issue "README 样张为横向展示图。"
```

只输出单条 record：

```powershell
python 工具/new_output_evaluation.py --prompt-pack dori_commercial_poster --image-file 预览图/example.jpg --record-only
```

输出后再用 `python 工具/validate_output_evaluations.py --file <文件> --check` 校验。

## summarize_output_evaluations.py

用途：读取结构化出图评分记录，生成平均分、决策分布、分项平均分、常见问题、失败类型分布和明细表。

生成默认汇总：

```powershell
python 工具/summarize_output_evaluations.py
```

默认输出：

```text
评估/出图评分汇总.md
```

检查汇总是否过期：

```powershell
python 工具/summarize_output_evaluations.py --check
```

## suggest_failure_fixes.py

用途：读取结构化出图评分记录里的 `failure_ids`，到 `评估/failure_fix_lexicon.json` 查找对应修正词，只为 `edit` / `regenerate` / `reject` 记录生成可复制的失败修正建议；`keep` 记录只进入汇总统计。

生成建议：

```powershell
python 工具/suggest_failure_fixes.py
```

默认输出：

```text
评估/失败修正建议.md
```

只检查是否同步：

```powershell
python 工具/suggest_failure_fixes.py --check
```

## build_project_dashboard.py

用途：汇总 Prompt Pack、角色、模板、tags、预览图、失败修正规则和结构化评分记录，生成项目全局仪表盘。

生成仪表盘：

```powershell
python 工具/build_project_dashboard.py
```

默认输出：

```text
评估/项目仪表盘.md
```

只检查是否同步：

```powershell
python 工具/build_project_dashboard.py --check
```

## validate_gpt_image2_parameters.py

用途：校验本仓库给 OpenAI `gpt-image-2` 使用的推荐尺寸档位，避免把 2:3 竖图误写成严格 9:16，或把不合规尺寸放进模板。

校验内置推荐档位：

```powershell
python 工具/validate_gpt_image2_parameters.py --check
```

检查单个尺寸是否接近 9:16：

```powershell
python 工具/validate_gpt_image2_parameters.py --size 1024x1824 --require-9-16
python 工具/validate_gpt_image2_parameters.py --size 1024x1536 --require-9-16
```

输出 Markdown 档位表：

```powershell
python 工具/validate_gpt_image2_parameters.py --markdown
```

## validate_api_requests.py

用途：校验 `生成提示词/prompt_packs.api_requests.jsonl` 和 `生成提示词/prompt_packs.api_requests.schema.json` 是否与 `配置/prompt_packs.json` 同步，确保批量请求草稿里的 `model`、`prompt`、`size`、`quality`、`output_format`、压缩参数和 tags 没有漂移，并拦截未知字段、空白 title/prompt 和重复 tags。

只检查是否同步：

```powershell
python 工具/validate_api_requests.py --check
```

## build_prompt_pack.py

用途：读取并校验 `配置/prompt_packs.json`，把角色锚点、输出类型、场景、构图、光线、材质、安全约束、防串约束和 gpt-image-2 推荐 `api_profile` 组合成可复制提示词；校验会拦截未知字段、空白文本、重复列表项、失效引用和漂移的 `api_profile`。
校验时还会读取 `配置/tag_taxonomy.json`，确保模板 tags 都来自受控词表，并检查标签词表未知字段、版本日期格式、分类 slug、空白文本和重复 alias；同时校验 `api_profile` 的 size、quality、output_format、output_compression 和 background，避免同义词或 API 参数漂移。
不依赖网络，适合本地快速出 prompt。

查看可用组合：

```powershell
python 工具/build_prompt_pack.py --list
```

按标签筛选：

```powershell
python 工具/build_prompt_pack.py --tag 公开安全
python 工具/build_prompt_pack.py --tag 商业海报
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

输出 JSON，方便接脚本、API 或前端；其中会包含可直接读取的 `api_profile`：

```powershell
python 工具/build_prompt_pack.py furina_convention_phone --format json
```

输出只包含 OpenAI 图片生成请求字段的单条 payload：

```powershell
python 工具/build_prompt_pack.py furina_convention_phone --format api-json
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
生成提示词/标签索引.md
生成提示词/标签覆盖矩阵.md
生成提示词/prompt_packs.generated.json
生成提示词/prompt_packs.generated.schema.json
生成提示词/prompt_packs.api_requests.jsonl
生成提示词/prompt_packs.api_requests.schema.json
生成提示词/prompt_packs.index.csv
```

`生成提示词/README.md` 会自动生成「角色 × 用途」快速复制入口，单个 Markdown 文件顶部会显示推荐 API 参数；`生成提示词/覆盖矩阵.md` 用于查看每个角色已经覆盖/缺失的输出类型，`生成提示词/标签索引.md` 用于按 tags 查找 Prompt Pack，`生成提示词/标签覆盖矩阵.md` 用于查看每个正式 tag 覆盖了哪些模板、角色和 Prompt Pack；`生成提示词/prompt_packs.generated.json` 用于脚本、API 或前端读取全部 Prompt Pack，并包含 `source_config_sha256`、tags 和 `api_profile` 方便核对来源配置、按用途筛选和直接接 API；`生成提示词/prompt_packs.generated.schema.json` 由导出工具同步生成，用于说明 JSON bundle 结构并约束非空白文本、slug ID 和 tags 去重；`生成提示词/prompt_packs.api_requests.jsonl` 是逐行请求草稿，适合批量脚本一行一条读取；`生成提示词/prompt_packs.api_requests.schema.json` 用于说明 JSONL 每一行的结构；`生成提示词/prompt_packs.index.csv` 用于表格筛选 Prompt Pack，包含 gpt-image-2 参数列和 tags 列。

`check_prompt_repo.py` 会检查这些导出文件是否和配置一致，也会间接检查 tags 是否已登记到 `配置/tag_taxonomy.json`；如果过期需要重新运行 `--all`。

## 工具测试

运行：

```powershell
python 工具/run_quality_gate.py
```

统一质量门禁会覆盖 Prompt Pack 配置未知字段/非空白文本/列表去重/ID slug、模板 `api_profile`、JSON bundle/schema 同步与结构约束、API 请求 JSONL 未知字段/非空白 prompt/tags 去重、标签 taxonomy 未知字段/日期格式/重复 alias、角色防串审计、Prompt 文本质量审计、Prompt 文本质量规则未知字段/非空白文本/列表去重、失败修正词库未知字段/非空白文本/列表去重、结构化出图评分 slug ID/未知字段/日期/图片路径/非空白文本/failure_ids 去重、评分汇总、评分骨架生成、失败修正建议、项目仪表盘、gpt-image-2 参数档位、仓库结构、Markdown 代码块闭合、预览图 manifest 结构/尺寸/安全状态、README 预览图 alt/caption/顺序、安全约束、文本文件 LF / BOM / 末尾换行、自动导出文件、Python 源码编译和单元测试。单元测试本身会覆盖 Prompt Pack 渲染、配置未知字段/非空白文本/列表去重/ID slug、api_profile 导出、JSON bundle/schema 同步、API JSON payload、tags 导出、API JSONL 未知字段/非空白 prompt/tags 去重、标签索引、标签 taxonomy 未知字段/日期格式/重复 alias、批量导出、CLI、预览图 manifest 结构/尺寸/安全状态、README 预览图 alt/caption/顺序、角色防串审计、Prompt 文本质量审计、Prompt 文本质量规则未知字段/非空白文本/列表去重、失败修正词库未知字段/非空白文本/列表去重、结构化出图评分 slug ID/未知字段/日期/图片路径/非空白文本/failure_ids 去重、评分汇总、评分骨架生成、失败修正建议、项目仪表盘、gpt-image-2 参数档位和统一质量门禁帮助入口。
