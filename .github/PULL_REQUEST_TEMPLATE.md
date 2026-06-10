# Pull Request 检查清单

## 改动类型

- [ ] 新增/修改角色提示词
- [ ] 新增/修改模板
- [ ] 新增/修改 Prompt Pack 配置
- [ ] 新增/修改生成提示词
- [ ] 工具脚本 / 测试 / CI
- [ ] 文档 / README / 参考仓库追踪

## 改动说明

请简要说明这次改了什么、为什么改。

## 安全与防串检查

- [ ] 保留“非低俗、不性感化、端庄自然”的约束。
- [ ] 角色文件包含明确的“不要混入其他角色元素”。
- [ ] 多格图/角色卡写了同一角色一致性。
- [ ] 文字类图写了“文字清晰、不要乱码”。
- [ ] 没有直接复制外部仓库长提示词。

## Prompt Pack 检查

如果修改了 `配置/prompt_packs.json`：

- [ ] 已运行 `python 工具/build_prompt_pack.py --validate`
- [ ] 已运行 `python 工具/build_prompt_pack.py --all`
- [ ] 已检查 `生成提示词/覆盖矩阵.md`

## 本地验证

- [ ] 已运行 `python 工具/check_prompt_repo.py`
- [ ] 已运行 `python -m unittest discover -s tests -v`
