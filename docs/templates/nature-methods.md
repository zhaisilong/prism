# Nature Methods

`nature-methods` / `journal/nature-methods` 是 Prism 维护的写作草稿，提供 `article`（默认）、`resource` 和 `analysis`。它使用标准 `article` 类，并非期刊官方模板，也不声称复刻最终出版版式。

```bash
scripts/latex-paper.sh --init projects/Papers/my-method --template nature-methods
scripts/latex-paper.sh --init projects/Papers/my-resource --template nature-methods --article-type resource
scripts/latex-paper.sh --init projects/Papers/my-analysis --template nature-methods --article-type analysis
```

三种稿件分别侧重方法与验证、资源内容与可获得性、已有方法的比较；示例内容和数值均为合成排版材料。离线初始化默认使用 XeLaTeX，支持中文和中英混排；`--language english` 使用 pdfLaTeX。两种模式均使用 BibTeX，不自动翻译。

[期刊稿型说明](https://www.nature.com/nmeth/content)为三类稿件均列出：摘要不超过 150 词且不含参考文献；通常正文 3,000 词（编辑可酌情放宽至 5,000 词），最多 6 个图表，参考文献建议约 50 条。正文按无标题引言、Results、Discussion 和 Online Methods 组织，Results 和 Methods 使用专题小标题，Discussion 不使用小标题。请核对当前指南及编辑意见；Prism 不自动检查投稿合规性。

独立补充材料和 Extended Data 分别使用各自的编号；正文引用应与实际提交材料一致。下面的命令保留主文重建入口，`examples.tex` 可用同样方式独立编译：

```bash
scripts/latex-paper.sh projects/Papers/my-method --main supplementary.tex --no-build-script
scripts/latex-paper.sh projects/Papers/my-method --main extended_data.tex --no-build-script
```

[初投说明](https://www.nature.com/nmeth/submission-guidelines/initial-formatting)允许使用编译后的 PDF，初稿无需特殊排版。[原则接收后（AIP）的格式要求](https://www.nature.com/nmeth/submission-guidelines/aip-and-formatting)则要求标准文档类、单一 TeX 文本、默认 Computer Modern 字体以及嵌入正文的数字参考文献，并对 Extended Data 和补充材料作出具体规定。本草稿的 BibTeX 与中英混排设置用于写作；最终投稿文件须由作者依指南另行整理，Prism 不自动打包。

按稿件适用情况核对 [Nature Portfolio 的 Reporting Summary 要求](https://www.nature.com/nature/editorial-policies/reporting-standards)与期刊编辑意见；官方也提供[表单参考副本](https://www.nature.com/documents/nr-reporting-summary-flat.pdf)，请通过期刊获取适用的最新版填写文件。模板不复制或自动填写官方表单；数据和代码可用性、作者贡献、资助与利益冲突声明均须据实填写。

[返回模板目录](../templates.md) · [日常使用](../guide.zh-CN.md) · [高级用法](../reference.zh-CN.md)
