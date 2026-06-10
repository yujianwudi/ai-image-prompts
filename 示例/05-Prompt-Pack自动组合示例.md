# Prompt Pack 自动组合示例

这个示例展示怎么用机器可读配置直接组合提示词。  
配置来源：`../配置/prompt_packs.json`  
构建工具：`../工具/build_prompt_pack.py`

## 1. 查看可用组合

```powershell
python 工具/build_prompt_pack.py --list
```

当前可用：

```text
furina_convention_phone
furina_readme_preview
citlali_character_card
citlali_vertical_thumbnail
dori_commercial_poster
```

## 2. 输出一条完整提示词

```powershell
python 工具/build_prompt_pack.py furina_convention_phone
```

输出会自动包含：

- 主体锁定
- 必须保留
- 场景环境
- 动作/表情
- 版式构图
- 光线色彩
- 材质细节
- 文字策略
- 安全约束
- 防串约束
- 质量约束

## 3. 保存成 Markdown

```powershell
python 工具/build_prompt_pack.py citlali_character_card --format markdown --out 示例/自动生成-茜特菈莉角色卡.md
```

## 4. 推荐修改方式

不要直接改输出结果。  
建议先改：

```text
配置/prompt_packs.json
```

然后重新运行构建命令。这样角色锚点和防串约束不会漏。

## 5. 适合什么时候用

- 想快速生成稳定提示词。
- 想让同一个角色套不同输出类型。
- 想检查角色锚点和安全约束有没有丢。
- 想把后续模板做成更标准的 Prompt as Code。
