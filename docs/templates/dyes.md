# Dyes and Pigments

`dyes` / `journal/dyes-and-pigments` 提供 Prism 维护的 `research`（默认）和 `review` 写作骨架，面向 Elsevier 的 Dyes and Pigments。它是投稿草稿，不是期刊专用官方模板，也不声称复刻最终出版版式。

```bash
scripts/latex-paper.sh --init projects/Papers/my-dyes --template dyes
scripts/latex-paper.sh --init projects/Papers/my-review --template dyes --article-type review
```

草稿参考 Elsevier 署名的 [Overleaf `elsarticle` 通用模板](https://www.overleaf.com/latex/templates/elsevier-article-elsarticle-template/vdzfjgjbckgz)，复用本地 TeX 发行版提供的 `elsarticle` 和 `elsarticle-num`。正文数字引用按出现顺序排列，支持 DOI；这是写作时的引用配置，投稿前仍须核对期刊要求。初始化无需联网；默认 XeLaTeX 支持中英混排，创建时加 `--language english` 使用 pdfLaTeX，两种模式均使用 BibTeX，系统不会自动翻译。

Research 骨架用于组织引言、设计与合成、表征、结果讨论和结论；Review 使用主题章节、批判性比较与展望。图、表、Scheme 和公式均为合成排版示例，不代表研究结果；使用前请替换为作者核实的内容。补充材料 `supplementary.tex` 独立编译，页码、图、表和公式采用 S 编号。图文摘要 `graphical_abstract.tex` 和 `highlights.txt` 是可删除的写作辅助，不代表已核实的强制投稿材料。

```bash
scripts/latex-paper.sh projects/Papers/my-dyes --main supplementary.tex --no-build-script
scripts/latex-paper.sh projects/Papers/my-dyes --main graphical_abstract.tex --no-build-script
```

`examples.tex` 也可使用相同方式独立编译。`--no-build-script` 保留主文重建入口。

[期刊官方介绍](https://shop.elsevier.com/journals/dyes-and-pigments/0143-7208)说明其范围及不接收的主题，并要求综述作者在投稿前提交[提案表](https://legacyfileshare.elsevier.com/promis_misc/dypi-review-paper-proposal.docx)供编辑批准。2026-11-10 核查时，[期刊作者指南](https://www.sciencedirect.com/journal/dyes-and-pigments/publish/guide-for-authors)返回 403；摘要字数、图文摘要、Highlights 等具体要求尚未由该指南核实，请在投稿前重新查阅。模板不会自动提交提案或检查投稿合规性。

[返回模板目录](../templates.md) · [日常使用](../guide.zh-CN.md) · [高级用法](../reference.zh-CN.md)
