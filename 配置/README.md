# 配置

这里放机器可读的 Prompt as Code 配置。
目前核心文件是：

```text
配置/prompt_packs.json
配置/prompt_packs.schema.json
配置/tag_taxonomy.json
配置/tag_taxonomy.schema.json
```

## 用途

把角色锚点、输出类型、标签、场景、构图、光线、材质、文字策略、安全约束和防串约束拆成可复用字段。
这样以后新增角色或模板时，可以先更新配置，再用工具自动组合提示词。

## 使用命令

查看可用组合：

```powershell
python 工具/build_prompt_pack.py --list
```

输出某个组合：

```powershell
python 工具/build_prompt_pack.py furina_convention_phone
```

批量导出：

```powershell
python 工具/build_prompt_pack.py --all
```

默认输出到 `生成提示词/`。

保存到文件：

```powershell
python 工具/build_prompt_pack.py dori_commercial_poster --out 示例/自动生成-多莉商业海报.md
```

## JSON Schema

`prompt_packs.json` 已绑定本地 schema：

```json
"$schema": "prompt_packs.schema.json"
```

支持 JSON Schema 的编辑器可以根据 `配置/prompt_packs.schema.json` 提示字段结构。质量门禁也会检查 `$schema` 是否存在、是否指向配置目录内的 schema 文件，角色/模板/Pack ID 是否保持小写 slug，并用生成器复核模板 `api_profile` 是否符合本仓库的 gpt-image-2 竖图约定。

`tag_taxonomy.json` 也绑定本地 schema：

```json
"$schema": "tag_taxonomy.schema.json"
```

新增模板标签前，先把标签登记到 `tag_taxonomy.json`，再写进 `prompt_packs.json`。

## 维护规则

- `characters` 放角色锚点、必须保留元素和禁止混入元素。
- `templates` 放输出类型、tags、gpt-image-2 `api_profile`、构图、光线、材质、文字策略和安全约束。
- `packs` 放具体组合案例，只引用已有角色和模板。
- `tags` 用于 JSON bundle、CSV 索引和前端筛选；每个模板必须包含 `公开安全`，并且必须来自 `tag_taxonomy.json` 的正式标签。
- `api_profile` 用于记录推荐 `model`、`size`、`quality`、`output_format`、`output_compression` 和 `background`；jpeg/webp 必须写 0-100 压缩率，png 不写压缩率，并会进入 JSON bundle、CSV 索引、API 请求 JSONL 和 JSONL schema 校验流程。
- 同义词不要直接写进模板 tags，例如 `商业海报图` 应登记为 `商业海报` 的 alias，模板里仍使用正式标签 `商业海报`。
- 不要把外部仓库的长提示词直接复制进配置，只保留结构化字段。

## 当前覆盖

当前 `prompt_packs.json` 已覆盖三位角色与五类输出类型：

- 芙宁娜 Furina
- 茜特菈莉 Citlali
- 多莉 Dori

输出类型：

- 写实 cos 手机随手拍
- GitHub README 公开预览图
- 角色参考卡
- 商业联名海报 / 电商主图
- 竖版社媒封面缩略图

具体覆盖情况看：

```text
生成提示词/覆盖矩阵.md
```

按标签筛选看：

```text
生成提示词/标签索引.md
```

也可以直接运行：

```powershell
python 工具/build_prompt_pack.py --tag 公开安全
```
