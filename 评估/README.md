# 出图评估与迭代流程

这个文件夹用于记录「生成后怎么判断好不好、怎么修、怎么继续迭代」。

## 推荐流程

```text
1. 先生成一张图
2. 用评分表检查是否可用
3. 找出失败类型
4. 判断：重新生成 / 图像编辑修正
5. 记录本轮提示词、问题、修正词和结果
6. 把有效修正沉淀回模板
```

## 什么时候重新生成

适合重新生成：

- 构图完全错了。
- 场景完全不对。
- 角色身份大面积串掉。
- 风格方向错了，比如变成插画/CG。

## 什么时候用图像编辑

适合图像编辑：

- 图整体不错，只是发型、头饰、服装细节错。
- 场景对了，但有少量角色污染。
- 光线、背景、姿势很好，只需要修正局部。
- 想把已有图改成更适合 README 公开展示的版本。

## 关键原则

- 不要每次都整段重写提示词。
- 先定位问题，再加最小修正。
- 多格图优先检查角色一致性。
- 公开展示图优先检查是否端庄、非低俗、无乱码。

## 角色防串审计

如果是维护角色设定或 Prompt Pack，优先看自动生成的审计报告：

```text
评估/角色防串审计报告.md
```

生成或检查报告：

```powershell
python 工具/audit_character_prompts.py
python 工具/audit_character_prompts.py --check
```

统一质量门禁会自动检查这份报告是否过期。

## Prompt 文本质量审计

如果是维护 Prompt Pack 文本结构、模板字段或全局质量约束，优先看：

```text
评估/Prompt文本质量审计报告.md
```

规则文件：

```text
评估/prompt_quality_rules.json
评估/prompt_quality_rules.schema.json
```

生成或检查报告：

```powershell
python 工具/lint_prompt_quality.py
python 工具/lint_prompt_quality.py --check
```

统一质量门禁会自动检查这份报告是否过期。

## 结构化失败修正词库

如果是维护「失败类型 → 修正词」映射，优先改机器可读 JSON：

```text
评估/failure_fix_lexicon.json
评估/failure_fix_lexicon.schema.json
```

生成或检查可读版 Markdown：

```powershell
python 工具/validate_failure_fix_lexicon.py
python 工具/validate_failure_fix_lexicon.py --check
```

默认输出：

```text
评估/失败修正词库.md
```

统一质量门禁会自动检查 JSON 结构、核心失败类型、必含修正词，以及 Markdown 是否同步。

## 结构化出图评分记录

Markdown 评分表适合人工快速判断；如果要沉淀多轮出图结果，可以复制这个 JSON 示例：

```text
评估/output_evaluations.example.json
```

结构规则：

```text
评估/output_evaluations.schema.json
```

校验记录：

```powershell
python 工具/validate_output_evaluations.py --check
```

它会检查评分总分是否等于各项分数之和、Prompt Pack/角色引用是否存在、图片路径是否存在、decision 是否合法。

自动生成汇总：

```powershell
python 工具/summarize_output_evaluations.py
python 工具/summarize_output_evaluations.py --check
```

默认输出：

```text
评估/出图评分汇总.md
```


## 仓库质量门禁

如果是维护仓库结构、模板文件和 README，先看：

```text
评估/仓库质量门禁.md
```

本地运行：

```powershell
python 工具/run_quality_gate.py
```
