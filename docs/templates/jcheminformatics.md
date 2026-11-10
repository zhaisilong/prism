# Journal of Cheminformatics

`jcheminformatics` 是 Prism 为 Journal of Cheminformatics 研究论文维护的原创草稿，不是期刊官方模板。按[期刊研究论文要求](https://link.springer.com/journal/13321/submission-guidelines/research)，摘要不超过 350 词，其中 Scientific Contribution 不超过 3 句；提供 3–10 个关键词，并说明数据和代码可用性。模板示例仅作排版占位，数据、代码和结论由作者提供。期刊的[格式说明](https://link.springer.com/journal/13321/submission-guidelines)要求双倍行距、行号和页码，并建议官方 Springer Nature LaTeX 模板；上传 TeX 时由期刊系统使用 pdfLaTeX 和 TeX Live 2021 编译，提交前应核查兼容性。可用 `--language english` 初始化英文 pdfLaTeX 草稿；中文模式用于写作。

独立示例可用 `scripts/latex-paper.sh PROJECT --main examples.tex --no-build-script` 构建。模板负责写作与编译支持；投稿前由作者核对当前期刊指南，字数、提案和投稿规则不属于自动合规检查。

[返回模板目录](../templates.md) · [日常使用](../guide.zh-CN.md) · [高级用法](../reference.zh-CN.md)
