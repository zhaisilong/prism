# Nature

`nature` / `journal/nature` 是 Prism 维护的 Nature 本刊写作草稿，默认离线创建；Nature Machine Intelligence 使用单独的 [`nmi`](nmi.md) 入口。草稿使用标准 `article` 类，并非出版社的本刊专用 class，也不声称复刻最终成刊版式。

```bash
scripts/latex-paper.sh --init projects/Papers/my-nature --template nature
scripts/latex-paper.sh projects/Papers/my-nature --strict
```

默认 XeLaTeX 支持中英混排；初始化时加 `--language english` 使用 pdfLaTeX。两种模式均使用 BibTeX，系统不会自动翻译。图表与示例均为合成占位，正式使用前请替换。独立补充材料和 `examples.tex` 用 `--main 文件名 --no-build-script` 构建，以保留主文重建入口。

[Nature 初投说明](https://www.nature.com/nature/for-authors/initial-submission)允许灵活组织初稿；[最终投稿说明](https://www.nature.com/nature/for-authors/final-submission)对单一 TeX 文件、标准 class 和内嵌数字参考文献另有要求。Prism 草稿不自动整理最终投稿包。

旧 `family/nature-nmi` 标识、已有项目和官方 `sn-jnl` 项目保持兼容；显式本地官方 ZIP 导入的旧用法见[高级用法](../reference.zh-CN.md)。新建 NMI 项目请使用 `--template nmi`。

[返回模板目录](../templates.md) · [日常使用](../guide.zh-CN.md) · [高级用法](../reference.zh-CN.md)
