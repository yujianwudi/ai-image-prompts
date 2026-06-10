# 贡献说明

欢迎补充新角色、新模板、新示例。  
为了避免越改越乱，建议按下面规则提交。

## 目录规则

```text
角色/     放角色专属提示词
模板/     放通用模板、场景、镜头、灯光、参数、负面词
示例/     放完整可复制的一键提示词
预览图/   放压缩后的公开预览图
评估/     放评分表、失败修正和迭代记录
参考仓库/ 放外部仓库追踪、分类映射和持续优化流程
工具/     放维护脚本
配置/     放机器可读 Prompt Pack 配置
生成提示词/ 放自动导出的可复制提示词
.github/     放 GitHub Actions、Issue 模板和 PR 模板
```

## 新增角色

新增角色时，建议放在：

```text
角色/04-角色名-提示词.md
```

文件结构建议：

1. 角色锁定目标
2. 不能丢的识别点
3. 完整正向提示词
4. gpt-image-2 自然语言版
5. 专属约束 / 防串词
6. 快速检查

## 新增模板

新增模板时，先判断属于哪类：

- 场景模板
- 镜头构图
- 灯光色彩
- 真实材质
- 情绪动作
- 负面约束
- 商业海报 / 电商
- 信息图 / UI
- 角色卡 / 分镜
- 封面缩略图
- 长图教程 / Slides
- 地图 / 导览图
- Prompt as Code 字段模板

不要把所有内容塞进一个文件。

如果参考外部仓库，只提炼分类、版式、变量和失败修正思路，不直接搬运长提示词。

## 风格要求

- 优先自然语言，少堆关键词。
- 必须保留非低俗、安全、端庄的约束。
- 多格图必须写角色一致性约束。
- 有文字的图必须写「文字清晰、不要乱码」。
- 不要直接复制其他仓库的长提示词，提炼结构后重写。

## 出图示例入库标准

建议满足：

- 角色一致性明显。
- 端庄、非低俗、适合公开展示。
- 没有明显乱码、水印或错误logo。
- 文件已压缩，不要直接提交超大原图。
- 能说明对应模板的用途。

## 新增 Prompt Pack

新增自动组合提示词时，优先修改：

```text
配置/prompt_packs.json
```

规则：

- 新角色放进 `characters`，必须写 `must_keep` 和 `avoid`。
- 新输出类型放进 `templates`，必须写 `safety`，并包含“非低俗、不性感化”。
- 新组合放进 `packs`，只能引用已存在的角色和模板。
- 修改后运行 `python 工具/build_prompt_pack.py --validate`、`python 工具/build_prompt_pack.py --all` 和 `python 工具/check_prompt_repo.py`。
- 新增 pack 后检查 `生成提示词/覆盖矩阵.md`，确认覆盖缺口符合预期。

## 提交前检查

提交前建议运行：

```powershell
python 工具/check_prompt_repo.py
python -m unittest discover -s tests -v
```

必须保证：

- 角色文件保留非低俗、不性感化和不要混入其他角色元素的约束。
- 本地 Markdown 链接和 README 预览图路径存在。
- 新模板能在 `模板/README.md` 或 `参考仓库/分类映射表.md` 里找到对应分类。
- 如果改动工具脚本，需要补充或更新 `tests/` 下的测试。
- 不直接复制外部仓库长提示词。

## Issue / PR 模板

公开协作时优先使用 GitHub 模板：

```text
.github/ISSUE_TEMPLATE/character_prompt.yml
.github/ISSUE_TEMPLATE/template_optimization.yml
.github/ISSUE_TEMPLATE/output_issue.yml
.github/PULL_REQUEST_TEMPLATE.md
```

这些模板会提醒提交者写清角色锚点、防串要求、安全约束、文字清晰和本地验证结果。
