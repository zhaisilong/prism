# 论文模板选型与来源

核查日期：2026-10-24。Prism 版本和上游模板版本分别记录；“可初始化”表示已提供接入流程，具体期刊的投稿要求仍以官网为准。

## 可直接初始化

| 标识 | 用途 | 引擎 / 文献 | 文件来源 |
| --- | --- | --- | --- |
| `prism`（默认） | 通用科研草稿、中英混排、复杂图表公式与补充材料 | XeLaTeX 或 LuaLaTeX / BibTeX | Prism 原创模板，MIT |
| `nature` | Nature Portfolio / NMI 初稿写作 | pdfLaTeX / BibTeX，`sn-nature` | Prism 原创启动文件 + 本地获取的官方 Springer Nature 3.1 文件 |
| `nature-communications` | Nature Communications 研究论文草稿 | pdfLaTeX / BibTeX | Prism 原创 `article` 草稿，MIT |
| `bib` | Briefings in Bioinformatics 英文稿、双栏图表与公式 | pdfLaTeX / BibTeX | Prism 原创启动文件 + 官方 OUP 1.5 class |
| `ddt` | Drug Discovery Today 单栏叙述性综述草稿 | pdfLaTeX / BibTeX，数字上标 | Prism 原创启动文件 + TeX Live 安装的 Elsevier `elsarticle` |
| `jcim` | Journal of Chemical Information and Modeling 研究论文草稿 | pdfLaTeX / BibTeX | Prism 原创启动文件 + TeX Live 安装的 ACS `achemso` 宏包 |
| `science-advances` | Science Advances 研究论文草稿 | pdfLaTeX / BibTeX | Prism 原创启动文件 + 本地导入 Science-family v1.0 样式 |

`prism` 的 `main.tex` 分节写作；期刊模板主文是单一 TeX，不加载 Prism 字体样式。各模板均附 `examples.tex`；Science Advances 在 `main.tex` 中合并补充材料，其余模板有独立 `supplementary.tex`。所有演示均为格式示例。

已在临时目录严格编译各模板的主文、补充材料和示例，检查代表页面；Prism 另通过 LuaLaTeX 构建。独立补充材料与示例使用 `--no-build-script` 保留主文重建入口。

Nature 官方包来自 [Springer Nature 作者支持页](https://www.springernature.com/gp/authors/campaigns/latex-author-support)，也可从[官方 Overleaf 模板](https://www.overleaf.com/latex/templates/springer-nature-latex-template/myxmhdsbzkyd)查看。接入实现固定下载地址、版本与 SHA-256，并保留下载的完整 ZIP。上游 class/BST 保留其许可，不纳入 Prism MIT，也不上传到公开代码库。

NMI 提供[初稿要求](https://www.nature.com/natmachintell/submission-guidelines/initial-formatting)和[接收后格式要求](https://www.nature.com/natmachintell/submission-guidelines/aip-and-formatting)。`sn-jnl` 是官方提供的可选方案；不要把它理解为 NMI 强制 class，或宣称本模板已完成最终投稿整理。

Nature Communications 允许首次提交合并正文和图的 PDF，补充材料单独提供。根据[投稿说明](https://www.nature.com/ncomms/submit/how-to-submit)，修订稿的 TeX 需使用标准文档类，将参考文献并入单一正文 `.tex`，不接受单独的 `.bib`。此模板使用 BibTeX 辅助写初稿，不自动整理最终投稿文件。

BIB 使用 [OUP 作者模板](https://ctan.org/pkg/oup-authoring-template) 1.5（2026-07-14），采用 `unnumsec,webpdf,contemporary,large`，使用该版本默认的数字引用；旧期刊配置表中的 `numbered` 在新版 class 中会干扰编号，因此省略。首次初始化校验官方 ZIP 后将所需文件存入本地项目，离线可用 `--template-source`。主文为官方双栏，独立补充材料使用标准 `article` 单栏；参考文献使用 `unsrt` 按首次引用顺序编号。最终格式以 [BIB 作者指南](https://academic.oup.com/bib/pages/author-guidelines)和 [OUP 模板说明](https://academic.oup.com/pages/for-authors/journals/preparing-and-submitting-your-manuscript)为准。上游文件保留 LPPL 许可，公开仓库只保存原创启动稿与导入代码。

DDT 使用发行版中的 [Elsevier 官方 `elsarticle` 类](https://www.elsevier.com/en-gb/researcher/author/policies-and-guidelines/latex-instructions)与 `elsarticle-num.bst`，不下载或复制第三方源码。`review` 模式为单栏、1.5 倍行距；数字上标及按引用顺序列参考文献作为草稿样式，参考 [DDT 已发表综述](https://www.sciencedirect.com/science/article/pii/S1359644625000546)。`highlights.txt`、`teaser.txt` 为可选占位。2026-10-27 核查时，[DDT 作者指南](https://www.sciencedirect.com/journal/drug-discovery-today/publish/guide-for-authors)无法访问，投稿前应确认当前要求；此模板不承诺最终出版格式。

JCIM 使用 [ACS 官方示例](https://www.overleaf.com/latex/templates/latex-template-for-american-chemical-society-acs-journal-submissions/swszwgfqsshj)支持的 `article` + `achemso` / BibTeX 组合（官方示例默认使用 `biblatex` / Biber）；只依赖已安装的 TeX Live 宏包，不复制第三方代码。请替换目录图占位，并依照 [JCIM 作者指南](https://researcher-resources.acs.org/publish/author_guidelines?coden=jcisd8)核对投稿要求；本模板用于初稿，不自动整理最终投稿文件。

Science Advances 使用 [AAAS Science-family 官方模板](https://www.overleaf.com/latex/templates/latex-template-for-science-family-journals/kjytmmfyxthd) v1.0（2024-07）的 `scicite.sty` 和 `sciencemag.bst`。初始化从用户提供的本地目录或 ZIP 校验并复制原样式及版权说明；公开代码不附带这些文件。正文与补充材料使用一份连续编号的文献表。文件哈希用于版本一致性检查，不单独证明包的来源；修订稿要求以期刊最新说明为准，本模板不自动嵌入 `.bbl`。

## 其他高质量官方模板

以下为精选参考入口，本版本没有将它们注册为可初始化选项，也没有承诺在 Prism 中完成编译验证。

| 家族 | 适合场景 | 来源与注意事项 |
| --- | --- | --- |
| Elsevier `elsarticle` / CAS | Elsevier 期刊，含单双栏结构 | [elsarticle](https://ctan.org/pkg/elsarticle)、[CAS](https://ctan.org/pkg/els-cas-templates)；LPPL。按目标期刊选择 class，不自动替换现有稿件 |
| IEEEtran | 工程、电子、计算机期刊与会议 | [官方 CTAN 包](https://ctan.org/pkg/ieeetran)；LPPL。采用目标 venue 指定配置，稳定版本的更新时间不代表使用价值低 |
| ACM `acmart` | ACM 期刊与会议 | [官方 CTAN 包](https://ctan.org/pkg/acmart)；LPPL。生产稿使用正式发布版，格式参数由 venue 决定 |
| REVTeX | APS / AIP 等物理论文 | [APS 官方入口](https://journals.aps.org/revtex)、[CTAN](https://ctan.org/pkg/revtex)；LPPL。保留 class 的引用与版式规则 |

模板质量以官方来源、许可清晰、数学与图表能力和可重建性判断，不只看成刊视觉效果。接入更多模板时先在临时目录验证，再标记为支持；不从历史研究目录回收未知版本的第三方文件。
