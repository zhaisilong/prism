# Nature / NMI

Nature 默认使用 Prism 原创标准 `article` 草稿。需要官方 `sn-jnl` / `sn-nature` 时，用 `--template-source` 显式提供原始 3.1 ZIP；已有官方项目继续原样构建。官方包来自 [Springer Nature 作者支持页](https://www.springernature.com/gp/authors/campaigns/latex-author-support)。该 class 在 LPPL 声明外另有与 LaTeX base 一起分发的文字，因此本仓库不单独镜像它；这不影响其他可分发样式。
NMI 提供[初稿要求](https://www.nature.com/natmachintell/submission-guidelines/initial-formatting)和[接收后格式要求](https://www.nature.com/natmachintell/submission-guidelines/aip-and-formatting)。`sn-jnl` 是官方提供的可选方案；不要把它理解为 NMI 强制 class，或宣称本模板已完成最终投稿整理。

独立示例可用 `scripts/latex-paper.sh PROJECT --main examples.tex --no-build-script` 构建。模板负责写作与编译支持；投稿前由作者核对当前期刊指南，字数、提案和投稿规则不属于自动合规检查。

[返回模板目录](../templates.md) · [日常使用](../guide.zh-CN.md) · [高级用法](../reference.zh-CN.md)
