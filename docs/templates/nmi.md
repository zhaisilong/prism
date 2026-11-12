# Nature Machine Intelligence

`nmi` / `journal/nature-machine-intelligence` 是 Prism 维护的离线写作草稿，提供 `article`（默认）、`analysis` 和 `review`。Nature 本刊使用 [`nature`](nature.md) 入口。该草稿不是官方专用 class，也不声称复刻成刊版式。

```bash
scripts/latex-paper.sh --init projects/Papers/my-nmi --template nmi
scripts/latex-paper.sh --init projects/Papers/my-analysis --template nmi --article-type analysis
scripts/latex-paper.sh --init projects/Papers/my-review --template nmi --article-type review
```

Article 侧重研究问题与证据，Analysis 侧重系统性分析，Review 侧重文献综合与批判性讨论。所有图、表、数值和示例均为合成占位，不代表研究结果。默认 XeLaTeX 支持中文和中英混排；创建时加 `--language english` 使用 pdfLaTeX，两者均使用 BibTeX，不自动翻译。

独立补充材料使用 `scripts/latex-paper.sh PROJECT --main supplementary.tex --no-build-script`；共享示例同样指定 `--main examples.tex --no-build-script`，以保留主文重建入口。

参见[期刊稿型](https://www.nature.com/natmachintell/content)、[初投说明](https://www.nature.com/natmachintell/submission-guidelines/initial-formatting)及[接收后格式要求](https://www.nature.com/natmachintell/submission-guidelines/aip-and-formatting)。2026-11-11 核查时，这些页面直接访问会跳转至登录；稿型信息参考官方页面的搜索索引，投稿前须重新核对当前要求。Prism 不自动判断投稿合规性或整理最终投稿包。

[返回模板目录](../templates.md) · [日常使用](../guide.zh-CN.md) · [高级用法](../reference.zh-CN.md)
