# Prism LaTeX

**从中文草稿到期刊模板，让论文排版更顺手。**

Prism 是面向 Codex 和命令行的本地 LaTeX 工作流：选择模板、写入内容、生成 PDF，也能整理已有论文的图表与版式。论文之外，同一仓库还提供笔记和审稿意见的排版工具。

## 项目特色

<!-- prism:template-count:start -->
- **20 套离线模板**：覆盖化学、生物信息学与综合期刊，按出版社分组查询；可选稿型由目录统一列出，模板资源随仓库提供。
<!-- prism:template-count:end -->
- **先用中文写，再整理英文稿**：以英文期刊结构和版式为基础，默认支持中文及中英混排，保留英文与数学排版；系统不自动翻译。
- **让图表适应目标模板**：辅助检查并纠正迁移遗留的字体、图注、表格宽度与图片尺寸，保留科研内容、数值和面板标识；图内字体需要可编辑绘图源配合调整。
- **构建干净、方便重建**：统一命令在临时目录编译，提供严格检查和重建入口；编译失败保留已有 PDF。
- **正文与补充材料一起考虑**：支持 BibTeX 参考文献、图表公式示例及补充材料；按模板保留独立 S 编号或合并结构。
- **研究资料留在本地**：`projects/` 默认忽略；公开同步使用精确文件清单、敏感信息检查和独立代码历史，发布前审核差异。

设计思路与日常操作见[简明使用指南](docs/guide.zh-CN.md)。

## 安装

```bash
git clone https://github.com/zhaisilong/prism.git
python3 prism/scripts/install-paper-skill.py
```

编译需要 Python 3.9+、TeX Live 和 `latexmk`，具体步骤见 [macOS / Linux 安装指南](docs/install.zh-CN.md)。已有完整仓库时，在根目录运行 `python3 scripts/install-paper-skill.py` 即可安装或更新论文入口。

## 开始写论文

直接告诉 Codex：

> 用 $paper-latex 的 Nature 模板创建一篇论文，放在 `projects/Papers/my-paper`，并编译检查。

也可以在 Prism 根目录完成三步：

```bash
# 1. 按出版社查看模板与稿型
scripts/latex-templates.sh

# 2. 创建论文项目
scripts/latex-paper.sh --init projects/Papers/my-paper --template nature

# 3. 编译 PDF
scripts/latex-paper.sh projects/Papers/my-paper
```

修改 `main.tex`、`references.bib` 和相应正文文件后，重复第三步即可更新 PDF。

已有论文可以这样说：

> 用 $paper-latex 按 JACS 模板整理这份论文，纠正遗留图表格式，保留内容和数据，先给我副本预览。

## 模板一览

<!-- prism:template-catalog:start -->
| 出版社 / 类别 | 模板短名称 |
| --- | --- |
| AAAS | [`science-advances`](docs/templates/science-advances.md) |
| ACS | [`chemrev`](docs/templates/chemrev.md)、[`jcim`](docs/templates/jcim.md)、[`jmc`](docs/templates/jmc.md)、[`jacs`](docs/templates/jacs.md) |
| Elsevier | [`ddt`](docs/templates/ddt.md)、[`dyes`](docs/templates/dyes.md)、[`ejmc`](docs/templates/ejmc.md) |
| Oxford University Press | [`bioinformatics`](docs/templates/bioinformatics.md)、[`bib`](docs/templates/bib.md)、[`nar`](docs/templates/nar.md) |
| Royal Society of Chemistry | [`rsc-advances`](docs/templates/rsc-advances.md) |
| Springer Nature | [`jcheminformatics`](docs/templates/jcheminformatics.md)、[`nature`](docs/templates/nature.md)、[`nature-communications`](docs/templates/nature-communications.md)、[`nmi`](docs/templates/nmi.md)、[`nature-methods`](docs/templates/nature-methods.md) |
| Wiley-VCH | [`advanced-science`](docs/templates/advanced-science.md)、[`angew`](docs/templates/angew.md) |
| 通用 | [`prism`](docs/templates/prism.md) |
<!-- prism:template-catalog:end -->

将创建命令中的 `nature` 换成相应短名称即可。多稿型模板可加 `--article-type`，例如 `--template angew --article-type review`。完整名称、规范 ID 和默认稿型以 `scripts/latex-templates.sh` 输出为准；原有 `scripts/latex-paper.sh --list-templates` 保留平铺输出。

Nature 本刊使用 `--template nature`；Nature Machine Intelligence 使用 `--template nmi`，可选 `article`、`analysis` 和 `review`，两者均可离线创建。

RSC Advances 使用 `--template rsc-advances`；综述加 `--article-type review`，详见[模板说明](docs/templates/rsc-advances.md)。

想看一个模板的引擎、文档和来源，运行 `scripts/latex-templates.sh --show advanced-science`；维护者可用 `--validate` 离线检查全部模板资源。详细规则只需阅读所选模板的说明。

JMC 使用 `--template jmc`，综述型稿件选 `--article-type perspective`；EJMC 使用 `--template ejmc`，综述选 `--article-type review`。两刊均默认研究论文，详见 [JMC](docs/templates/jmc.md) 与 [EJMC](docs/templates/ejmc.md) 说明。

Chemical Reviews 常规综述可直接用 `--template chemrev` 创建；提案要求、目录和 TOC 图说明见[模板说明](docs/templates.md#chemical-reviews)。

Advanced Science 使用 `--template advanced-science`，默认研究论文；可加 `--article-type review` 或 `--article-type perspective`，见[三类模板说明](docs/templates.md#advanced-science)。它属于 Wiley-VCH；表中的 `science-advances` 属于 AAAS。

新建项目默认支持中英混排，期刊模板使用 XeLaTeX；期刊项目创建时加 `--language english` 可选择英文 pdfLaTeX 模式，不执行翻译。已有项目保留原编译模式，参考文献目前使用英文条目。Nature 默认采用 Prism 维护的 `article` 初稿；各模板的官方来源、衍生关系和适用范围见[模板来源说明](docs/templates.md)。

## 更新与维护

从 GitHub 克隆的副本可用 `git pull --ff-only` 更新模板与实现；仓库移动后重新运行安装命令。版本以 `VERSION` 为准，采用日期版本。

研究文件放在 `projects/`。维护者公开同步时，只导出审核过的代码、模板和通用文档；整文件保护与敏感信息扫描用于辅助检查，仍需审核发布清单和修改差异。操作见[公开同步说明](docs/public-sync.md)。

[安装 LaTeX](docs/install.zh-CN.md) · [三步使用指南](docs/guide.zh-CN.md) · [模板来源](docs/templates.md) · [高级用法](docs/reference.zh-CN.md)

Prism 自有代码与模板采用 [MIT License](LICENSE)；第三方文件及衍生样式保留相应许可和署名。开发维护规则见 [AGENTS.md](AGENTS.md)。
