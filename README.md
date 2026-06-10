# AI 生图提示词模板库

[![validate-prompt-repo](https://github.com/yujianwudi/ai-image-prompts/actions/workflows/validate.yml/badge.svg)](https://github.com/yujianwudi/ai-image-prompts/actions/workflows/validate.yml)
![Prompt Packs](https://img.shields.io/badge/Prompt%20Packs-15-blue)
![Characters](https://img.shields.io/badge/Characters-3-purple)
![Templates](https://img.shields.io/badge/Templates-25%2B-green)
![Schema](https://img.shields.io/badge/JSON%20Schema-enabled-orange)


用于整理 AI 生图提示词、角色专属设定、固定场景模板和防串提示词。  
当前主要围绕写实 cosplay、室内漫展手机随手拍、9:16 竖图、真实服装材质和非低俗风格来整理。

模板已增加 OpenAI `gpt-image-2` 优化写法：更偏自然语言分段描述，少堆关键词，多写清楚主体、场景、构图、光线、材质和约束。

## 预览图

下面是部分生成效果预览，图片已压缩后放在 `预览图/` 文件夹，方便 GitHub README 直接展示。

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

1. 想最快开始，可以先运行 `python 工具/build_prompt_pack.py --list` 查看可自动组合的提示词。
2. 打开 `示例/README.md`，复制一个完整示例提示词。  
3. 如果要换角色，去 `角色/README.md` 复制对应角色专属词。  
4. 如果要换画面类型，去 `模板/README.md` 选择场景、镜头、灯光、材质和约束。  
5. 使用 OpenAI `gpt-image-2` 时，优先使用自然语言分段写法，不要只堆关键词。  
6. 生成后如果串角色，用 `示例/04-通用gpt-image-2编辑修正.md` 做二次修正。
7. 出图后用 `评估/出图评分表.md` 判断能不能公开交付。

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

每次新增角色、模板、预览图后，建议运行：

```powershell
python 工具/check_prompt_repo.py
```

如果想跑工具单元测试：

```powershell
python -m unittest discover -s tests -v
```

如果想重新导出全部 Prompt Pack：

```powershell
python 工具/build_prompt_pack.py --all
```

这个脚本会检查目录结构、本地链接、README 预览图引用、角色安全约束、参考仓库追踪、Prompt Pack 配置和自动导出文件。GitHub Actions 也会在 push / pull request 时自动运行质量检查和单元测试。

## 当前重点

- 角色设定防串：芙宁娜、茜特菈莉、朵莉亚/多莉。
- 固定模板拆分：场景、镜头、灯光、材质、动作、负面词、平台参数。
- gpt-image-2 优化：把关键词模板改成自然语言分段提示词。
- gpt-image-2 一键模板：写实cos、README预览图、角色卡、三视图、九宫格、商业海报、图像编辑。
- Prompt as Code 字段化：把任务类型、主体锁定、版式、文字策略和防串约束拆开。
- 机器可读 Prompt Pack：通过 `配置/prompt_packs.json` 和 `工具/build_prompt_pack.py` 自动组合可复制提示词。
- JSON Schema：`配置/prompt_packs.schema.json` 为 Prompt Pack 配置提供字段结构约束。
- Prompt Pack 覆盖矩阵：通过 `生成提示词/覆盖矩阵.md` 查看每个角色缺哪些输出类型。
- 三角色 × 五输出类型已完整覆盖：写实随手拍、README预览、角色卡、商业海报、竖版封面。
- 参考优秀仓库补充：商业海报、电商主图、信息图、UI截图、角色卡、分镜板、九宫格、封面缩略图、长图教程、地图导览模板。
- README 预览图：展示模板生成效果，避免只看文字不直观。
- 评估迭代：出图评分、失败修正词库、迭代记录模板。
- Issue / PR 模板：规范角色新增、模板优化、出图问题反馈和提交检查。
- 仓库格式规范：通过 `.gitattributes` 和 `.editorconfig` 固定 UTF-8、LF 和缩进规则。

## 交付文档

- `示例/README.md`：完整可复制提示词示例。
- `评估/README.md`：出图评估与迭代流程。
- `评估/仓库质量门禁.md`：仓库结构、链接、安全约束和 CI 检查规则。
- `参考仓库/README.md`：外部 awesome 仓库追踪与分类映射。
- `工具/README.md`：维护脚本说明。
- `配置/README.md`：机器可读 Prompt Pack 配置说明。
- `生成提示词/README.md`：由 Prompt Pack 自动导出的可复制提示词。
- `CONTRIBUTING.md`：新增角色和模板的规则。
- `免责声明.md`：公开使用、版权和安全提醒。
- `CHANGELOG.md`：变更记录。
