# 配置

这里放机器可读的 Prompt as Code 配置。  
目前核心文件是：

```text
配置/prompt_packs.json
```

## 用途

把角色锚点、输出类型、场景、构图、光线、材质、文字策略、安全约束和防串约束拆成可复用字段。  
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

保存到文件：

```powershell
python 工具/build_prompt_pack.py dori_commercial_poster --out 示例/自动生成-多莉商业海报.md
```

## 维护规则

- `characters` 放角色锚点、必须保留元素和禁止混入元素。
- `templates` 放输出类型、构图、光线、材质、文字策略和安全约束。
- `packs` 放具体组合案例，只引用已有角色和模板。
- 不要把外部仓库的长提示词直接复制进配置，只保留结构化字段。
