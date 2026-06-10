# Security Policy

This repository is a prompt-template and documentation project.  
For content-safety, prompt-safety, privacy, or public-preview concerns, please see:

```text
内容安全政策.md
授权与使用边界.md
```

Please report issues through the GitHub issue templates, especially:

```text
.github/ISSUE_TEMPLATE/output_issue.yml
```

Do not include private personal data, sensitive images, credentials, or non-public material in issues or pull requests.

The local quality gate runs a lightweight secret scan for common API keys and tokens:

```powershell
python 工具/run_quality_gate.py
```
