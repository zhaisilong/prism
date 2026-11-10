# European Journal of Medicinal Chemistry

`ejmc` / `journal/european-journal-of-medicinal-chemistry` 面向 Elsevier 的 European Journal of Medicinal Chemistry，提供 `research`（默认）和 `review` 两类 Prism 原创骨架。[官方期刊介绍](https://shop.elsevier.com/journals/european-journal-of-medicinal-chemistry/0223-5234)确认接收研究论文与批判性综述。

```bash
scripts/latex-paper.sh --init projects/Papers/my-ejmc --template ejmc
scripts/latex-paper.sh --init projects/Papers/my-review --template ejmc --article-type review
```

采用 [Elsevier 官方支持的 `elsarticle`](https://www.elsevier.com/researcher/author/policies-and-guidelines/latex-instructions) 和 `elsarticle-num`，由本地 TeX 发行版提供，使用 A4、`preprint,12pt` 单栏草稿。引用按首次出现顺序编号，正文为行内方括号，保留完整文章标题和可点击 DOI。该配置独立于 DDT，保持 DDT 的既有行距和上标引用。初始化离线完成，默认 XeLaTeX 支持中英混排；`--language english` 使用 pdfLaTeX，均使用 BibTeX，不自动翻译。

2026-11-08 核查时，[期刊作者指南](https://www.sciencedirect.com/journal/european-journal-of-medicinal-chemistry/publish/guide-for-authors)页面返回 403。本模板依据可访问的官方期刊介绍与 Elsevier LaTeX 说明维护写作草稿，不将未核实的摘要字数、邀请流程、关键词数量或图文摘要要求写成硬性规则；投稿前应重新查看当前作者指南。

Research 正文为 Introduction、Results and Discussion、Conclusion、Experimental，围绕实际设计、合成、表征和生物评价填写内容。Review 采用编号主题章节、批判性比较、Challenges and Outlook；不预填检索流程、研究结论或作者经历。Scheme、化学式、SAR 表、误差数值、多面板图和公式都是合成排版示例，须替换为真实内容。

项目附带独立 `graphical_abstract.tex`，默认横向图框 **120×48 mm**，以及可删除的 `highlights.txt`。它们是 Prism 写作辅助文件，框大小和占位不表示已核实的期刊强制要求。使用 `scripts/latex-paper.sh PROJECT --main graphical_abstract.tex --no-build-script` 生成图文摘要 PDF。

独立 `supplementary.tex` 首页包含标题、作者和目录，页码、图、表、Scheme 和公式采用 S 编号；填写实际附带的表征、额外分析或补充证据。使用 `--main supplementary.tex --no-build-script` 构建；共享图表公式示例使用 `--main examples.tex --no-build-script`，均保留主文重建入口。

数据可用性、作者贡献、资助、利益冲突及适用的伦理声明须由作者据实提供。模板支持写作与构建，不自动打包投稿源文件或认证投稿合规性。

[返回模板目录](../templates.md) · [日常使用](../guide.zh-CN.md) · [高级用法](../reference.zh-CN.md)
