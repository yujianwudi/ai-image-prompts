# 自动生成提示词

这里的文件由 `工具/build_prompt_pack.py --all` 根据 `配置/prompt_packs.json` 生成。
如果要修改内容，请优先修改配置，然后重新导出，不要手改生成文件。

## 重新生成

```powershell
python 工具/build_prompt_pack.py --all
```

## 文件列表

| Prompt Pack | 文件 | 说明 |
| --- | --- | --- |
| `furina_convention_phone` | `furina_convention_phone.md` | 芙宁娜室内漫展手机随手拍 |
| `furina_readme_preview` | `furina_readme_preview.md` | 芙宁娜 README 公开预览图 |
| `citlali_character_card` | `citlali_character_card.md` | 茜特菈莉角色参考卡 |
| `citlali_vertical_thumbnail` | `citlali_vertical_thumbnail.md` | 茜特菈莉角色防串教程封面 |
| `dori_commercial_poster` | `dori_commercial_poster.md` | 多莉商业联名海报 |
