# 三步写论文

Prism 以目标期刊的英文稿结构和版式为基础，默认支持中文和中英混排。中文支持主要补充中文字体，保留原有英文与数学排版。你可以先用中文组织内容，再整理为英文投稿稿；系统不会自动翻译。

- 标题、作者、正文、图表说明和补充材料均支持中文；默认章节标题仍为英文，可自行修改。
- 参考文献目前使用英文条目。
- 创建期刊项目时加上 `--language english` 可选择英文编译模式；它不执行翻译，已有项目也不会自动转换。

也可以直接告诉 Codex：

> 用 $paper-latex 的 Nature 模板创建论文，放在 `projects/Papers/my-paper`，并编译。

第一次使用先在完整仓库中运行 `python3 scripts/install-paper-skill.py` 安装入口。

自己操作时，在 Prism 根目录完成下面三步。

## 1. 选模板并创建

先查看按出版社分组的模板，以及各期刊支持的稿型：

```bash
scripts/latex-templates.sh
```

需要某个模板的引擎、稿型和文件说明时，用 `scripts/latex-templates.sh --show advanced-science`，将名称换成你选的模板即可。

<!-- prism:template-catalog:start -->
| 模板 | 期刊 / 用途 |
| --- | --- |
| [`science-advances`](templates/science-advances.md) | Science Advances |
| [`chemrev`](templates/chemrev.md) | Chemical Reviews |
| [`jcim`](templates/jcim.md) | Journal of Chemical Information and Modeling |
| [`jmc`](templates/jmc.md) | Journal of Medicinal Chemistry |
| [`jacs`](templates/jacs.md) | Journal of the American Chemical Society |
| [`ddt`](templates/ddt.md) | Drug Discovery Today |
| [`dyes`](templates/dyes.md) | Dyes and Pigments |
| [`ejmc`](templates/ejmc.md) | European Journal of Medicinal Chemistry |
| [`bioinformatics`](templates/bioinformatics.md) | Bioinformatics |
| [`bib`](templates/bib.md) | Briefings in Bioinformatics |
| [`nar`](templates/nar.md) | Nucleic Acids Research |
| [`jcheminformatics`](templates/jcheminformatics.md) | Journal of Cheminformatics |
| [`nature`](templates/nature.md) | Nature |
| [`nature-communications`](templates/nature-communications.md) | Nature Communications |
| [`nmi`](templates/nmi.md) | Nature Machine Intelligence |
| [`nature-methods`](templates/nature-methods.md) | Nature Methods |
| [`advanced-science`](templates/advanced-science.md) | Advanced Science |
| [`angew`](templates/angew.md) | Angewandte Chemie International Edition |
| [`prism`](templates/prism.md) | Prism |
<!-- prism:template-catalog:end -->

```bash
scripts/latex-paper.sh --init projects/Papers/my-paper --template nature
```

更换模板时，把 `nature` 换成表格中的标识。全部模板均可离线创建。Nature 默认是我们维护的标准 `article` 初稿；官方版式见[高级用法](reference.zh-CN.md)。

多稿型模板加上 `--article-type`，例如：

```bash
scripts/latex-paper.sh --init projects/Papers/my-review --template advanced-science --article-type review
```

可选值和默认值由查询命令列出；字数、提案及投稿要求集中在表格链接的模板说明中。

JMC 可选 `research`、`perspective`（观点综述）；EJMC 可选 `research`、`review`。例如 `--template jmc --article-type perspective` 或 `--template ejmc --article-type review`。

Dyes and Pigments 默认研究稿；综述使用 `--template dyes --article-type review`，并请先阅读[模板说明](templates/dyes.md)中的提案要求。

Nature Methods 默认 Article；Resource 或 Analysis 可选 `--template nature-methods --article-type resource` 或 `--article-type analysis`，详见[模板说明](templates/nature-methods.md)。

Nature 本刊使用 `--template nature`；Nature Machine Intelligence 使用 `--template nmi`，可选 `article`、`analysis` 和 `review`。

## 2. 写内容

打开项目文件夹，修改：

- `main.tex`：标题、作者和正文；Prism 模板的正文在 `sections/`。
- `references.bib`：参考文献。
- `supplementary.tex`：补充材料，需要时再写；Science Advances 的补充材料在 `main.tex` 中。

图表公式可参考 `examples.tex`。模板里的示例文字和数据在正式使用前替换。

已有稿件可以直接说：“用 $paper-latex 按 JACS 模板整理这份论文，纠正遗留图表格式，保留内容和数据，先给我副本预览。”系统会以目标模板为准逐项调整；图片内部的字体需要可编辑源图才能可靠修改。

## 3. 生成 PDF

```bash
scripts/latex-paper.sh projects/Papers/my-paper
```

打开项目文件夹里的 `main.pdf`。修改后重复这一步即可。

独立补充材料使用：

```bash
scripts/latex-paper.sh projects/Papers/my-paper --main supplementary.tex --no-build-script
```

输出为同目录下的 `supplementary.pdf`，并保留主文重建入口。独立图文摘要或示例同样指定实际文件名。

更多操作交给 Codex，例如：“编译补充材料”“把宽表排得更清楚”“修复编译报错”。官方模板导入、笔记、review 和排错见[高级用法](reference.zh-CN.md)。
