# 预览图

这里放适合公开 GitHub README 展示的压缩预览图。

## 清单

预览图元数据维护在：

```text
manifest.json
```

每张图片都需要记录：

- `file`：文件名。
- `character`：对应角色。
- `scene`：主要场景。
- `prompt_pack`：对应 Prompt Pack。
- `caption`：README 或文档展示时的短说明。
- `public_safe`：必须为 `true`，表示端庄、非低俗、不性感化、无水印、无真实品牌 logo。
- `notes`：补充说明。

## 入库标准

- 图片应压缩后提交，单张尽量低于 2MB。
- 必须适合公开 README 展示。
- 不要包含低俗、擦边、性感化、儿童化、隐私信息、真实品牌 logo、水印或乱码文字。
- 如果图片被 README 引用，必须同时出现在 `manifest.json`。
- 如果删除图片，也要同步删除 README 引用和 `manifest.json` 记录。

## 本地检查

```powershell
python 工具/run_quality_gate.py
```

质量门禁会检查图片文件、README 引用和 `manifest.json` 是否一致。
