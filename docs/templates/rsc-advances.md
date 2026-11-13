# RSC Advances

`rsc-advances` / `journal/rsc-advances` 提供 Prism 维护的双栏草稿：`research`（默认）和 `review`。它参考 [Royal Society of Chemistry 的文章模板](https://www.overleaf.com/latex/templates/royal-society-of-chemistry-article-template/vffpnxpmxdfz)，但使用 Prism 原创排版，并非官方模板或最终成刊版式。官方模板的再分发许可尚未核实，仓库不复制其文件。

```bash
scripts/latex-paper.sh --init projects/Papers/my-rsc --template rsc-advances
scripts/latex-paper.sh --init projects/Papers/my-review --template rsc-advances --article-type review
```

两个稿型均可离线创建；默认 XeLaTeX 支持中文和中英混排，创建时添加 `--language english` 使用 pdfLaTeX。两种模式均使用 BibTeX，不自动翻译；中文可用于草稿，投稿前须整理为英文。

Research 骨架包括 Introduction、Experimental、Results and Discussion 和 Conclusion；Review 使用主题章节、批判性比较和展望。图、表、Scheme、公式及数值均为合成示例，使用前须替换；数据可用性、作者贡献及利益冲突等声明请据实填写。文内上标引用按出现顺序编号，使用 TeX 发行版的 `rsc` 文献样式，并配置文章标题和 DOI。

正文末尾提供可删除的 TOC 图文占位；期刊对修回稿的 TOC 图要求最大 8×4 cm，采用至少 600 dpi 的 TIFF，并配 1–2 句、不超过 250 字符的可编辑文字，概述主要发现而非描述图片；正文占位不能替代提交材料。独立补充材料采用 S 编号；使用以下命令构建并保留主文重建入口。共享的 `examples.tex` 可用同样方式构建。

```bash
scripts/latex-paper.sh projects/Papers/my-rsc --main supplementary.tex --no-build-script
```

[期刊作者指南](https://www.rsc.org/publishing/publish-with-us/publish-a-journal-article/rsc-advances)说明研究论文和综述使用相同文章模板；综述应批判性讨论现有文献，不包含未发表研究。使用 LaTeX 投稿时需提供源文件和包含图片的 PDF。投稿前请核对最新要求；Prism 不自动检查投稿合规性或打包投稿文件。

[返回模板目录](../templates.md) · [日常使用](../guide.zh-CN.md) · [高级用法](../reference.zh-CN.md)
