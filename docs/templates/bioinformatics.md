# Bioinformatics

Bioinformatics 原始论文草稿与 BIB 共享仓库内的固定 OUP 1.5 class，使用 `oup-abbrvnat.bst`，使用 `namedate` 作者—年份引用，并提供结构化摘要。`contemporary,large` 实测单栏约 89.5 mm，[期刊指南](https://academic.oup.com/bioinformatics/pages/author-guidelines)列出 86 mm；初稿不承诺满足最终列宽或投稿格式。上游 class 可能报告 `Unused global option(s)`，但实测双栏和作者—年份引用生效。默认离线创建；`--template-source` 仅供显式导入相同官方 ZIP。

独立示例可用 `scripts/latex-paper.sh PROJECT --main examples.tex --no-build-script` 构建。模板负责写作与编译支持；投稿前由作者核对当前期刊指南，字数、提案和投稿规则不属于自动合规检查。

[返回模板目录](../templates.md) · [日常使用](../guide.zh-CN.md) · [高级用法](../reference.zh-CN.md)
