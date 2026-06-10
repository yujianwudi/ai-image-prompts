# AGENTS.md

这个文件给后续接手本仓库的 Codex / 自动化维护者看。范围是整个仓库。

## 项目定位

这是一个公开的 AI 生图提示词模板库，重点是：

- 写实 cosplay。
- 室内漫展手机随手拍。
- 9:16 竖图。
- 非低俗、不性感化、真实服装质感。
- 芙宁娜、茜特菈莉、多莉 / 朵莉亚三位角色防串。

不要把它当成普通代码仓库随便重构。这里很多文件是给人直接复制使用的提示词，改动要兼顾可读性、可复制性和公开安全。

## 必跑命令

提交前默认运行：

```powershell
python 工具/run_quality_gate.py
```

如果只改了 OpenAI `gpt-image-2` 参数、尺寸档位或平台说明，也可以先单独跑：

```powershell
python 工具/validate_gpt_image2_parameters.py --check
```

如果改了下面任何内容，优先运行刷新版：

```powershell
python 工具/run_quality_gate.py --refresh-generated
```

需要刷新版的情况：

- 修改 `配置/prompt_packs.json`。
- 修改 `工具/build_prompt_pack.py` 或 Prompt Pack 渲染逻辑。
- 修改 Prompt 文本质量规则、角色防串审计规则或出图评分汇总逻辑。
- 修改 `评估/failure_fix_lexicon.json` 或失败修正词库生成逻辑。
- 修改会影响 `生成提示词/` 自动导出结果的字段。
- 替换或新增预览图后，先运行 `python 工具/sync_preview_manifest.py`。

## 生成文件规则

不要手工编辑 `生成提示词/` 下的自动导出文件。

正确方式：

1. 改 `配置/prompt_packs.json` 或生成脚本。
2. 运行 `python 工具/run_quality_gate.py --refresh-generated`。
3. 检查 `生成提示词/README.md`、`生成提示词/覆盖矩阵.md`、`生成提示词/标签索引.md`、JSON bundle 和 CSV 索引是否符合预期。

## 提示词风格规则

OpenAI `gpt-image-2` 相关模板优先使用自然语言分段，不要只堆关键词。

推荐顺序：

1. 任务模式。
2. 不可变主体锚点。
3. 必须保留的角色识别点。
4. 场景环境。
5. 镜头构图。
6. 光线、色彩、材质。
7. 文字策略。
8. 安全约束和防串约束。

角色图里，发型、头饰、服装体系、关键道具和气质要比「高清、精致、氛围感」更靠前。

新增或修改 Prompt Pack 模板时，`templates.*.tags` 必须保留用途标签，并包含 `公开安全`。这些 tags 会进入 JSON bundle 和 CSV 索引，用于后续筛选。

严格 9:16 的 OpenAI 竖图参数优先写 `1024x1824`。`1024x1536` 是 2:3 备选，不要标成严格 9:16。
推荐尺寸档位和 API 约束先看 `模板/06-gpt-image-2官方规格自检清单.md`，机器校验入口是 `python 工具/validate_gpt_image2_parameters.py --check`。

不要把 Midjourney 参数写进 OpenAI API 参数，例如：

```text
--ar 9:16
--style raw
--stylize 50
```

## 角色防串规则

三位角色的专属锚点不能互相污染：

- 芙宁娜：白蓝短发、蓝黑小礼帽、枫丹蓝白歌剧服、水滴宝石、自信俏皮的歌剧感。
- 茜特菈莉：淡粉紫长发、前侧细辫、黑紫纳塔萨满服、冷淡安静神秘感。
- 多莉 / 朵莉亚：成年 coser、小个子表达、粉色卷发、方形眼镜、紫金商人帽、金币钱袋、小灯壶道具。

写茜特菈莉或多莉时，必须主动防止串到芙宁娜：

```text
不要混入芙宁娜的白蓝短发、蓝黑礼帽、枫丹蓝白歌剧服和水神舞台女王气质。
```

多莉必须保持成年化表达，可爱但不儿童化、不性感化。

## 内容安全规则

所有角色、模板、Prompt Pack、预览图和示例都要保持：

- 非低俗。
- 不性感化。
- 不儿童化。
- 不卧室暧昧感。
- 不使用真实个人隐私。
- 不使用真实品牌 logo 或真实平台水印。
- 不暗示官方授权或商用授权。

不要添加正式 `LICENSE` 文件，除非用户明确要求并确认授权方式。当前只维护 `授权与使用边界.md`。

## 预览图规则

新增或替换 `预览图/` 文件后：

1. 压缩图片，避免提交超大原图。
2. 更新 `预览图/manifest.json`。
3. 运行 `python 工具/sync_preview_manifest.py` 同步宽高、比例和方向。
4. 确认 `public_safe=true`。
5. 再运行 `python 工具/run_quality_gate.py`。

README 里的预览图必须登记在 manifest 里。

## 出图评分规则

维护 `评估/output_evaluations.example.json` 或新的评分日志时，除了写 `issues` 自由文本，也要写 `failure_ids`。`failure_ids` 必须引用 `评估/failure_fix_lexicon.json` 里已有的失败类型，方便后续汇总常见问题和修正方向。

修改评分记录或失败修正词库后，要同步检查 `评估/出图评分汇总.md` 和 `评估/失败修正建议.md`，不要手工改这两个生成报告。

## Git 与公开仓库规则

- 提交前确认 `git status --short --branch`。
- 不提交 `.env`、API key、GitHub token、未压缩原图、本地缓存和虚拟环境。
- 普通 `git push` 如果遇到网络问题，可以使用当前环境已有的安全备用推送方式；不要把 token、临时脚本或密钥提交进仓库。
- 推送后用 `gh run list --repo yujianwudi/ai-image-prompts --limit 5` 查看 CI。
- CI 失败时先看失败日志，不要盲改模板。

## 改动优先级

优先做能提升长期稳定性的改动：

1. 更强的角色防串。
2. 更清晰的模板分层。
3. 更可靠的生成 / 校验脚本。
4. 更准确的公开文档。
5. 更完整的测试和质量门禁。

不要为了看起来改动多而制造大范围无意义重写。
