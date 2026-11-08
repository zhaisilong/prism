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

| 模板 | 适合 |
| --- | --- |
| `nature` | Nature / NMI 论文初稿 |
| `nature-communications` | Nature Communications 研究论文 |
| `bib` | Briefings in Bioinformatics 论文 |
| `ddt` | Drug Discovery Today 单栏综述 |
| `jcim` | Journal of Chemical Information and Modeling 研究论文 |
| `jcheminformatics` | Journal of Cheminformatics 研究论文 |
| `jacs` | Journal of the American Chemical Society 研究论文 |
| `chemrev` | Chemical Reviews 常规综述 |
| `bioinformatics` | Bioinformatics 研究论文 |
| `nar` | NAR 研究论文、Database 或 Web Server 稿件 |
| `angew` | Angew 研究论文、Communication、Review、Minireview |
| `science-advances` | Science Advances 研究论文 |
| `prism` | 通用论文、中英混排 |

```bash
scripts/latex-paper.sh --init projects/Papers/my-paper --template nature
```

更换模板时，把 `nature` 换成表格中的标识。全部模板均可离线创建。Nature 默认是我们维护的标准 `article` 初稿；官方版式见[高级用法](reference.zh-CN.md)。

NAR 分别创建，普通研究稿可省略 `--article-type research`：

```bash
scripts/latex-paper.sh --init projects/Papers/nar-research --template nar --article-type research
scripts/latex-paper.sh --init projects/Papers/nar-database --template nar --article-type database
scripts/latex-paper.sh --init projects/Papers/nar-web-server --template nar --article-type web-server
```

NAR 初投提供完整 PDF，补充材料和图文摘要单独提供；修回需要可编辑源文件。Database 和 Web Server 均须先获得邀请；具体要求见[模板说明](templates.md#nar)。

Chemical Reviews 常规综述示例：

```bash
scripts/latex-paper.sh --init projects/Papers/chemrev-review --template chemrev
```

投稿须先受邀或通过提案。模板提供目录、作者简介及末页 TOC 图占位，按实际内容替换；详见[模板说明](templates.md#chemical-reviews)。

Angew 综述示例：

```bash
scripts/latex-paper.sh --init projects/Papers/angew-review --template angew --article-type review
```

稿型可选 `research`（默认）、`communication`、`review`、`minireview`。Angew 使用 Prism 维护的 Wiley 衍生草稿；Review／Minireview 需先向期刊提交综述提案，见[来源与说明](templates.md#angew)。

## 2. 写内容

打开项目文件夹，修改：

- `main.tex`：标题、作者和正文；Prism 模板的正文在 `sections/`。
- `references.bib`：参考文献。
- `supplementary.tex`：补充材料，需要时再写；Science Advances 的补充材料在 `main.tex` 中。
- NAR 的 `graphical_abstract.tex`：图文摘要；资源 URL、声明和图示占位均须替换。

图表公式可参考 `examples.tex`。模板里的示例文字和数据在正式使用前替换。

Angew 的 TOC 图文在主文末页；综述另有作者简介和肖像占位，按实际作者信息替换。

已有稿件可以直接说：“用 $paper-latex 按 JACS 模板整理这份论文，纠正遗留图表格式，保留内容和数据，先给我副本预览。”系统会以目标模板为准逐项调整；图片内部的字体需要可编辑源图才能可靠修改。

## 3. 生成 PDF

```bash
scripts/latex-paper.sh projects/Papers/my-paper
```

打开项目文件夹里的 `main.pdf`。修改后重复这一步即可。

NAR 的独立图文摘要可用 `scripts/latex-paper.sh 项目目录 --main graphical_abstract.tex --no-build-script` 编译；将文件名换成 `supplementary.tex` 则编译补充材料。输出位于同一项目目录。

更多操作交给 Codex，例如：“编译补充材料”“把宽表排得更清楚”“修复编译报错”。官方模板导入、笔记、review 和排错见[高级用法](reference.zh-CN.md)。
