# AI 生图提示词模板库

[![validate-prompt-repo](https://github.com/yujianwudi/ai-image-prompts/actions/workflows/validate.yml/badge.svg)](https://github.com/yujianwudi/ai-image-prompts/actions/workflows/validate.yml)
![Prompt Packs](https://img.shields.io/badge/Prompt%20Packs-15-blue)
![Characters](https://img.shields.io/badge/Characters-3-purple)
![Templates](https://img.shields.io/badge/Templates-25-green)
![Schema](https://img.shields.io/badge/JSON%20Schema-enabled-orange)
![Preview Images](https://img.shields.io/badge/Preview%20Images-4-lightgrey)


用于整理 AI 生图提示词、角色专属设定、固定场景模板和防串提示词。
当前主要围绕写实 cosplay、室内漫展手机随手拍、9:16 竖图、真实服装材质和非低俗风格来整理。

模板已按 2026-06-10 二次联网复核的 OpenAI `gpt-image-2` 图片生成资料优化：更偏自然语言分段描述，少堆关键词，先明确任务模式，再写不可变主体锚点、必须保留项、场景、构图、光线、材质、文字策略和安全防串约束；严格 9:16 竖图参数优先使用 `1024x1824`。

## 预览图

下面是部分生成效果预览，图片已压缩后放在 `预览图/` 文件夹，方便 GitHub README 直接展示。
这些预览图是 README 展示样张，`manifest.json` 会记录实际尺寸、方向和安全状态；正式 Prompt Pack 仍按各模板里的 9:16、角色卡或海报等输出规格执行。
预览图元数据记录在 `预览图/manifest.json`，结构规则见 `预览图/manifest.schema.json`，入库规则见 `预览图/README.md`。

<table>
  <tr>
    <td align="center">
      <img src="预览图/furina-dessert-01.jpg" width="220"><br>
      <sub>甜品店场景 / 写实cos</sub>
    </td>
    <td align="center">
      <img src="预览图/furina-dessert-02.jpg" width="220"><br>
      <sub>甜品店场景 / 道具互动</sub>
    </td>
    <td align="center">
      <img src="预览图/furina-night-01.jpg" width="220"><br>
      <sub>城市夜景 / 跟拍感</sub>
    </td>
    <td align="center">
      <img src="预览图/furina-night-02.jpg" width="220"><br>
      <sub>城市夜景 / 街拍感</sub>
    </td>
  </tr>
</table>

## 目录结构

这个项目按目录分类放：

```text
AGENTS.md
角色/
模板/
示例/
评估/
参考仓库/
工具/
配置/
生成提示词/
预览图/
```

## 3分钟快速开始

1. 想最快开始，可以打开 `生成提示词/README.md`，按「角色 × 用途」直接复制自动生成提示词。
2. 也可以运行 `python 工具/build_prompt_pack.py --list` 查看可自动组合的提示词。
3. 打开 `示例/README.md`，复制一个完整示例提示词。
4. 如果要换角色，去 `角色/README.md` 复制对应角色专属词。
5. 如果要换画面类型，去 `模板/README.md` 选择场景、镜头、灯光、材质和约束。
6. 使用 OpenAI `gpt-image-2` 时，优先使用自然语言分段写法，不要只堆关键词；角色图先写主体锁定，避免串到芙宁娜。
   如果不确定尺寸是否合规，可以先跑 `python 工具/validate_gpt_image2_parameters.py --size 1024x1824 --require-9-16`。
7. 生成后如果串角色，用 `示例/04-通用gpt-image-2编辑修正.md` 做二次修正。
8. 出图后用 `评估/出图评分表.md` 判断能不能公开交付。

## 角色

角色专属提示词都在：

```text
角色/README.md
```

里面放芙宁娜、茜特菈莉、朵莉亚/多莉的角色设定、正向词、反向词和防串提醒。

## 模板

通用固定模板都在：

```text
模板/README.md
```

里面按场景、镜头、灯光、材质、动作、负面词、平台参数分类。

## 推荐使用方式

```text
角色专属提示词 + 1个场景模板 + 1个镜头模板 + 1个灯光模板 + 1个材质模板 + 1组负面词 + 平台参数
```

不要一次性复制所有模板，容易互相污染。

## 质量检查

每次新增角色、模板、预览图后，优先运行统一质量门禁：

```powershell
python 工具/run_quality_gate.py
```

如果新增或替换了 `预览图/` 里的图片，先同步 manifest 尺寸元数据：

```powershell
python 工具/sync_preview_manifest.py
```

如果修改了 `配置/prompt_packs.json`，并且需要先重新导出全部 Prompt Pack：

```powershell
python 工具/run_quality_gate.py --refresh-generated
```

也可以单独运行底层命令：

```powershell
python 工具/build_prompt_pack.py --all
python 工具/build_prompt_pack.py --validate
python 工具/audit_character_prompts.py --check
python 工具/lint_prompt_quality.py --check
python 工具/validate_failure_fix_lexicon.py --check
python 工具/validate_output_evaluations.py --check
python 工具/summarize_output_evaluations.py --check
python 工具/suggest_failure_fixes.py --check
python 工具/validate_gpt_image2_parameters.py --check
python 工具/sync_preview_manifest.py --check
python 工具/check_prompt_repo.py
python -m unittest discover -s tests -v
```

统一质量门禁会检查 Prompt Pack 配置、标签 taxonomy、角色防串审计报告、Prompt 文本质量审计、失败修正词库、结构化出图评分记录与汇总、失败修正建议、gpt-image-2 参数档位、预览图 manifest 尺寸元数据、目录结构、本地链接、README 预览图引用、角色安全约束、参考仓库追踪、自动导出文件和单元测试。GitHub Actions 也会在 push / pull request 时自动运行同一个入口。

## 当前重点

- 角色设定防串：芙宁娜、茜特菈莉、朵莉亚/多莉。
- 固定模板拆分：场景、镜头、灯光、材质、动作、负面词、平台参数。
- gpt-image-2 优化：已联网复核 OpenAI 官方图片生成资料，把关键词模板改成「任务模式 → 不可变主体锚点 → 必须保留 → 可变画面 → 约束」结构，并补充严格 9:16 尺寸建议 `1024x1824`、短文字策略、图像编辑保留项和参数避坑。
- gpt-image-2 参数自检：`模板/06-gpt-image-2官方规格自检清单.md` 和 `工具/validate_gpt_image2_parameters.py` 会校验推荐尺寸档位，避免把 `1024x1536` 误写成严格 9:16，或把 Midjourney 参数混进 OpenAI API。
- gpt-image-2 一键模板：写实cos、README预览图、角色卡、三视图、九宫格、商业海报、图像编辑。
- Prompt as Code 字段化：把任务类型、主体锁定、版式、文字策略和防串约束拆开。
- 机器可读 Prompt Pack：通过 `配置/prompt_packs.json` 和 `工具/build_prompt_pack.py` 自动组合可复制提示词。
- 标签 taxonomy：通过 `配置/tag_taxonomy.json` 约束 Prompt Pack 模板 tags，避免标签同义词漂移，`商业海报图` 这类 alias 不能直接进模板。
- JSON 输出：`工具/build_prompt_pack.py --format json` 可输出带元数据的提示词记录，方便接 API、脚本或前端。
- 全量 JSON Bundle：`生成提示词/prompt_packs.generated.json` 自动导出全部 Prompt Pack，并由 `生成提示词/prompt_packs.generated.schema.json` 描述结构；bundle 内含 `source_config_sha256` 和 tags，方便前端或自动化工具核对来源配置并筛选用途。
- CSV 索引：`生成提示词/prompt_packs.index.csv` 自动列出 Prompt Pack、角色、模板、tags 和文件名，方便表格筛选。
- 标签索引：`生成提示词/标签索引.md` 自动按 tags 分组 Prompt Pack，也可以用 `python 工具/build_prompt_pack.py --tag 商业海报` 查询。
- 标签覆盖矩阵：`生成提示词/标签覆盖矩阵.md` 自动显示每个正式 tag 覆盖了哪些模板、角色和 Prompt Pack，方便发现标签空转或覆盖不足。
- JSON Schema：`配置/prompt_packs.schema.json` 为 Prompt Pack 配置提供字段结构约束。
- Prompt Pack 覆盖矩阵：通过 `生成提示词/覆盖矩阵.md` 查看每个角色缺哪些输出类型。
- Prompt Pack 快速复制入口：通过 `生成提示词/README.md` 按「角色 × 用途」直接选提示词。
- 三角色 × 五输出类型已完整覆盖：写实随手拍、README预览、角色卡、商业海报、竖版封面。
- 参考优秀仓库补充：商业海报、电商主图、信息图、UI截图、角色卡、分镜板、九宫格、封面缩略图、长图教程、地图导览模板。
- README 预览图：展示模板生成效果，避免只看文字不直观。
- 预览图清单：通过 `预览图/manifest.json` 和 `预览图/manifest.schema.json` 记录文件、尺寸、方向、角色、场景、Prompt Pack 和公开安全状态。
- 预览图元数据同步：通过 `工具/sync_preview_manifest.py` 自动刷新 manifest 中的宽高、比例和方向。
- 评估迭代：出图评分、失败修正词库、迭代记录模板。
- Issue / PR 模板：规范角色新增、模板优化、出图问题反馈和提交检查。
- 仓库格式规范：通过 `.gitattributes` 和 `.editorconfig` 固定 UTF-8、LF 和缩进规则。
- 忽略规则：通过 `.gitignore` 避免提交缓存、虚拟环境、本地密钥和未压缩原图。
- 密钥扫描：质量门禁会检查常见 API key、GitHub token、AWS key 和高风险明文 secret。
- 内容安全政策：明确非低俗、不性感化、不儿童化、隐私和真实品牌 logo 规则。
- 授权与使用边界：明确原创模板、第三方角色 IP、预览图和商用场景的边界。
- 统一质量门禁：`工具/run_quality_gate.py` 统一串起 Prompt Pack 校验、仓库检查和单元测试。
- 角色防串审计：`评估/角色防串审计报告.md` 自动汇总三角色锚点、防串、安全和成人化约束覆盖。
- Prompt 文本质量审计：`评估/Prompt文本质量审计报告.md` 自动检查生成前 prompt 的结构、安全、质量、模板意图、角色词和长度范围。
- 结构化失败修正词库：`评估/failure_fix_lexicon.json` 记录失败类型、识别线索、修正词和下一步动作，并自动生成 `评估/失败修正词库.md`。
- 结构化出图评分：`评估/output_evaluations.example.json` 和 `评估/output_evaluations.schema.json` 可记录每张图的评分、问题、失败类型 ID 和下一步动作。
- 出图评分汇总：`评估/出图评分汇总.md` 自动汇总平均分、决策分布、常见问题、失败类型分布和记录明细。
- 失败修正建议：`评估/失败修正建议.md` 自动把评分记录里的 `failure_ids` 转成可复制修正提示词。

## 交付文档

- `示例/README.md`：完整可复制提示词示例。
- `评估/README.md`：出图评估与迭代流程。
- `评估/仓库质量门禁.md`：仓库结构、链接、安全约束和 CI 检查规则。
- `评估/角色防串审计报告.md`：由工具自动生成的角色防串覆盖报告。
- `评估/Prompt文本质量审计报告.md`：由工具自动生成的 Prompt 文本质量预检报告。
- `评估/failure_fix_lexicon.json`：机器可读失败修正词库。
- `评估/失败修正词库.md`：由结构化失败修正词库自动生成的可复制修正词。
- `评估/output_evaluations.example.json`：结构化出图评分记录示例。
- `评估/出图评分汇总.md`：由结构化评分记录自动生成的汇总报告。
- `评估/失败修正建议.md`：由结构化评分记录和失败修正词库自动生成的可复制修正建议。
- `参考仓库/README.md`：外部 awesome 仓库追踪与分类映射。
- `工具/README.md`：维护脚本说明。
- `配置/README.md`：机器可读 Prompt Pack 配置说明。
- `生成提示词/README.md`：由 Prompt Pack 自动导出的可复制提示词。
- `生成提示词/标签索引.md`：由 Prompt Pack tags 自动导出的筛选入口。
- `预览图/README.md`：公开预览图入库规则和 manifest 维护说明。
- `CONTRIBUTING.md`：新增角色和模板的规则。
- `AGENTS.md`：后续 Codex / 自动化维护者的仓库操作指引。
- `免责声明.md`：公开使用、版权和安全提醒。
- `授权与使用边界.md`：原创提示词、第三方 IP、预览图和正式许可证边界说明。
- `内容安全政策.md`：公开预览图、Issue/PR 和 Prompt Pack 的安全规则。
- `SECURITY.md`：GitHub 安全入口，指向内容安全政策。
- `CHANGELOG.md`：变更记录。
