# 自动生成提示词

这里的文件由 `工具/build_prompt_pack.py --all` 根据 `配置/prompt_packs.json` 生成。
如果要修改内容，请优先修改配置，然后重新导出，不要手改生成文件。

## 重新生成

```powershell
python 工具/run_quality_gate.py --refresh-generated
```

## 快速复制入口

不知道选哪条时，按用途选：

- **看角色是否串**：优先复制 `写实 cos 手机随手拍`。
- **放 README 公开展示**：优先复制 `GitHub README 公开预览图`。
- **检查发型、头饰、服装细节**：优先复制 `角色参考卡`。
- **做宣传图或电商视觉**：优先复制 `商业联名海报 / 电商主图`。
- **做教程封面**：优先复制 `竖版社媒封面缩略图`。

### 按角色 × 用途

| 角色 | 写实 cos 手机随手拍 | GitHub README 公开预览图 | 角色参考卡 | 商业联名海报 / 电商主图 | 竖版社媒封面缩略图 |
| --- | --- | --- | --- | --- | --- |
| 芙宁娜 Furina | [`furina_convention_phone`](furina_convention_phone.md) | [`furina_readme_preview`](furina_readme_preview.md) | [`furina_character_card`](furina_character_card.md) | [`furina_commercial_poster`](furina_commercial_poster.md) | [`furina_vertical_thumbnail`](furina_vertical_thumbnail.md) |
| 茜特菈莉 Citlali | [`citlali_convention_phone`](citlali_convention_phone.md) | [`citlali_readme_preview`](citlali_readme_preview.md) | [`citlali_character_card`](citlali_character_card.md) | [`citlali_commercial_poster`](citlali_commercial_poster.md) | [`citlali_vertical_thumbnail`](citlali_vertical_thumbnail.md) |
| 多莉 Dori | [`dori_convention_phone`](dori_convention_phone.md) | [`dori_readme_preview`](dori_readme_preview.md) | [`dori_character_card`](dori_character_card.md) | [`dori_commercial_poster`](dori_commercial_poster.md) | [`dori_vertical_thumbnail`](dori_vertical_thumbnail.md) |

### 命令行复制

```powershell
python 工具/build_prompt_pack.py furina_convention_phone
python 工具/build_prompt_pack.py citlali_readme_preview
python 工具/build_prompt_pack.py dori_character_card
```

输出 Markdown 文件：

```powershell
python 工具/build_prompt_pack.py dori_commercial_poster --format markdown --out 示例/自动生成-多莉商业海报.md
```

输出 JSON 给脚本或前端使用：

```powershell
python 工具/build_prompt_pack.py furina_convention_phone --format json
```

## 覆盖矩阵

- [`覆盖矩阵.md`](覆盖矩阵.md)：查看每个角色已覆盖/未覆盖的输出类型。

## 文件列表

| Prompt Pack | 文件 | 说明 |
| --- | --- | --- |
| `furina_convention_phone` | `furina_convention_phone.md` | 芙宁娜室内漫展手机随手拍 |
| `furina_readme_preview` | `furina_readme_preview.md` | 芙宁娜 README 公开预览图 |
| `furina_character_card` | `furina_character_card.md` | 芙宁娜角色参考卡 |
| `furina_commercial_poster` | `furina_commercial_poster.md` | 芙宁娜枫丹甜品联名海报 |
| `furina_vertical_thumbnail` | `furina_vertical_thumbnail.md` | 芙宁娜角色防串教程封面 |
| `citlali_convention_phone` | `citlali_convention_phone.md` | 茜特菈莉室内漫展手机随手拍 |
| `citlali_readme_preview` | `citlali_readme_preview.md` | 茜特菈莉 README 公开预览图 |
| `citlali_character_card` | `citlali_character_card.md` | 茜特菈莉角色参考卡 |
| `citlali_commercial_poster` | `citlali_commercial_poster.md` | 茜特菈莉夜神主题联名海报 |
| `citlali_vertical_thumbnail` | `citlali_vertical_thumbnail.md` | 茜特菈莉角色防串教程封面 |
| `dori_convention_phone` | `dori_convention_phone.md` | 多莉室内漫展手机随手拍 |
| `dori_readme_preview` | `dori_readme_preview.md` | 多莉 README 公开预览图 |
| `dori_character_card` | `dori_character_card.md` | 多莉角色参考卡 |
| `dori_commercial_poster` | `dori_commercial_poster.md` | 多莉商业联名海报 |
| `dori_vertical_thumbnail` | `dori_vertical_thumbnail.md` | 多莉角色防串教程封面 |
