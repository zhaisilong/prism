# 论文模板选型与来源

模板分发与许可核查日期：2026-10-27。Prism 版本和上游模板版本分别记录；“可初始化”表示已提供接入流程，具体期刊的投稿要求仍以官网为准。

## 可直接初始化

| 标识 | 用途 | 引擎 / 文献 | 文件来源 |
| --- | --- | --- | --- |
| `prism`（默认） | 通用科研草稿、中英混排、复杂图表公式与补充材料 | XeLaTeX 或 LuaLaTeX / BibTeX | Prism 原创模板，MIT |
| `nature` | Nature Portfolio / NMI 初稿写作 | XeLaTeX / BibTeX | Prism 原创 `article` 初稿；可显式本地导入官方版式 |
| `nature-communications` | Nature Communications 研究论文草稿 | XeLaTeX / BibTeX | Prism 原创 `article` 草稿，MIT |
| `bib` | Briefings in Bioinformatics 论文、双栏图表与公式 | XeLaTeX / BibTeX | Prism 原创启动文件 + 仓库维护的 OUP 1.5 class |
| `ddt` | Drug Discovery Today 单栏叙述性综述草稿 | XeLaTeX / BibTeX，数字上标 | Prism 原创启动文件 + TeX Live 安装的 Elsevier `elsarticle` |
| `jcim` | Journal of Chemical Information and Modeling 研究论文草稿 | XeLaTeX / BibTeX | Prism 原创启动文件 + TeX Live 安装的 ACS `achemso` 宏包 |
| `jcheminformatics` | Journal of Cheminformatics 研究论文草稿 | XeLaTeX / BibTeX | Prism 基于标准 `article` 维护的原创草稿 |
| `jacs` | Journal of the American Chemical Society 研究论文草稿 | XeLaTeX / BibTeX | Prism 原创启动文件 + TeX Live 安装的 ACS `achemso` 宏包 |
| `chemrev` | Chemical Reviews 常规综述草稿 | XeLaTeX / BibTeX，数字上标 | Prism 原创 `article` 骨架 + TeX Live 安装的 ACS `achemso` 宏包 |
| `bioinformatics` | Bioinformatics 原始论文草稿 | XeLaTeX / BibTeX，作者—年份 | Prism 原创启动文件 + 仓库维护的 OUP 1.5 class 和样式 |
| `nar` | NAR 研究、Database 和 Web Server 稿件 | XeLaTeX / BibTeX，顺序编号 | Prism 三类骨架 + OUP 1.5 Modern Large + Prism 适配的引用样式 |
| `angew` | Angew 研究、Communication、Review、Minireview 草稿 | XeLaTeX / BibTeX，顺序编号 | Prism 维护的 Wiley／Overleaf 衍生 class 与原创四类骨架 |
| `science-advances` | Science Advances 研究论文草稿 | XeLaTeX / BibTeX | Prism 原创启动文件 + 仓库维护的 Science-family v1.0 样式 |

全部默认模板均可离线初始化，新项目默认支持中英混排；期刊模板用 XeLaTeX，通用 `prism` 可用 XeLaTeX 或 LuaLaTeX。期刊项目创建时可用 `--language english` 选择原 pdfLaTeX 模式。参考文献使用英文条目。编译依赖由 TeX 发行版提供。

`prism` 的 `main.tex` 分节写作；期刊模板主文是单一 TeX，仅加载提供中文字体的轻量样式，不叠加 Prism 的英文字体和版式。各模板均附 `examples.tex`；Science Advances 在 `main.tex` 中合并补充材料，其余模板有独立 `supplementary.tex`。所有演示均为格式示例。

以上为简短别名。运行 `scripts/latex-paper.sh --list-templates` 可查看以 `journal/`、`family/` 或 `generic/` 开头的完整名称和分类；旧命令及已有项目无需改动。

模板注册字段和未来会议扩展方式见[维护说明](template-registry.md)。

在临时目录严格编译各模板中英混排的主文、补充材料和示例，检查代表页面；Prism 另通过 LuaLaTeX 构建。独立补充材料与示例使用 `--no-build-script` 保留主文重建入口。

Nature 默认使用 Prism 原创标准 `article` 草稿。需要官方 `sn-jnl` / `sn-nature` 时，用 `--template-source` 显式提供原始 3.1 ZIP；已有官方项目继续原样构建。官方包来自 [Springer Nature 作者支持页](https://www.springernature.com/gp/authors/campaigns/latex-author-support)。该 class 在 LPPL 声明外另有与 LaTeX base 一起分发的文字，因此本仓库不单独镜像它；这不影响其他可分发样式。
NMI 提供[初稿要求](https://www.nature.com/natmachintell/submission-guidelines/initial-formatting)和[接收后格式要求](https://www.nature.com/natmachintell/submission-guidelines/aip-and-formatting)。`sn-jnl` 是官方提供的可选方案；不要把它理解为 NMI 强制 class，或宣称本模板已完成最终投稿整理。

Nature Communications 允许首次提交合并正文和图的 PDF，补充材料单独提供。根据[投稿说明](https://www.nature.com/ncomms/submit/how-to-submit)，修订稿的 TeX 需使用标准文档类，将参考文献并入单一正文 `.tex`，不接受单独的 `.bib`。此模板使用 BibTeX 辅助写初稿，不自动整理最终投稿文件。

BIB 使用 [OUP 作者模板](https://ctan.org/pkg/oup-authoring-template) 1.5（2026-07-14），采用 `unnumsec,webpdf,contemporary,large`，使用该版本默认的数字引用；旧期刊配置表中的 `numbered` 在新版 class 中会干扰编号，因此省略。初始化验证并复制仓库内固定版本的 class 和版权文件；高级用法仍可用 `--template-source` 导入固定官方 ZIP。主文为官方双栏，独立补充材料使用标准 `article` 单栏；参考文献使用 `unsrt` 按首次引用顺序编号。最终格式以 [BIB 作者指南](https://academic.oup.com/bib/pages/author-guidelines)和 [OUP 模板说明](https://academic.oup.com/pages/for-authors/journals/preparing-and-submitting-your-manuscript)为准。上游文件以原始许可公开，源码、README、上游 manifest 和删减说明集中保存在 `assets/upstream/oup/1.5/`。

DDT 使用发行版中的 [Elsevier 官方 `elsarticle` 类](https://www.elsevier.com/en-gb/researcher/author/policies-and-guidelines/latex-instructions)与 `elsarticle-num.bst`，不下载或复制第三方源码。`review` 模式为单栏、1.5 倍行距；数字上标及按引用顺序列参考文献作为草稿样式，参考 [DDT 已发表综述](https://www.sciencedirect.com/science/article/pii/S1359644625000546)。`highlights.txt`、`teaser.txt` 为可选占位。2026-10-27 核查时，[DDT 作者指南](https://www.sciencedirect.com/journal/drug-discovery-today/publish/guide-for-authors)无法访问，投稿前应确认当前要求；此模板不承诺最终出版格式。

JCIM 使用 [ACS 官方示例](https://www.overleaf.com/latex/templates/latex-template-for-american-chemical-society-acs-journal-submissions/swszwgfqsshj)支持的 `article` + `achemso` / BibTeX 组合（官方示例默认使用 `biblatex` / Biber）；只依赖已安装的 TeX Live 宏包，不复制第三方代码。请替换目录图占位，并依照 [JCIM 作者指南](https://researcher-resources.acs.org/publish/author_guidelines?coden=jcisd8)核对投稿要求；本模板用于初稿，不自动整理最终投稿文件。

`jcheminformatics` 是 Prism 为 Journal of Cheminformatics 研究论文维护的原创草稿，不是期刊官方模板。按[期刊研究论文要求](https://link.springer.com/journal/13321/submission-guidelines/research)，摘要不超过 350 词，其中 Scientific Contribution 不超过 3 句；提供 3–10 个关键词，并说明数据和代码可用性。模板示例仅作排版占位，数据、代码和结论由作者提供。期刊的[格式说明](https://link.springer.com/journal/13321/submission-guidelines)要求双倍行距、行号和页码，并建议官方 Springer Nature LaTeX 模板；上传 TeX 时由期刊系统使用 pdfLaTeX 和 TeX Live 2021 编译，提交前应核查兼容性。可用 `--language english` 初始化英文 pdfLaTeX 草稿；中文模式用于写作。

JACS 复用相同 ACS 构建，提供 Research Article 草稿、目录图占位和独立补充材料；提交前请查阅 [JACS 作者指南](https://researcher-resources.acs.org/publish/author_guidelines?coden=jacsat)。

Bioinformatics 原始论文草稿与 BIB 共享仓库内的固定 OUP 1.5 class，使用 `oup-abbrvnat.bst`，使用 `namedate` 作者—年份引用，并提供结构化摘要。`contemporary,large` 实测单栏约 89.5 mm，[期刊指南](https://academic.oup.com/bioinformatics/pages/author-guidelines)列出 86 mm；初稿不承诺满足最终列宽或投稿格式。上游 class 可能报告 `Unused global option(s)`，但实测双栏和作者—年份引用生效。默认离线创建；`--template-source` 仅供显式导入相同官方 ZIP。

Science Advances 使用 [AAAS Science-family 官方模板](https://www.overleaf.com/latex/templates/latex-template-for-science-family-journals/kjytmmfyxthd) v1.0（2024-07）的 `scicite.sty` 和 `sciencemag.bst`。初始化从仓库复制已校验的原样式及版权说明，无需用户提供目录或 ZIP；本地导入仍作为高级选项保留。正文与补充材料使用一份连续编号的文献表。文件哈希用于版本一致性检查，不单独证明包的来源；修订稿要求以期刊最新说明为准，本模板不自动嵌入 `.bbl`。

## Chemical Reviews

`chemrev` / `journal/chemical-reviews` 提供 Prism 维护的常规 Review 草稿，暂不包含 Focus Review。创建时直接选择 `--template chemrev`，不使用 `--article-type`。采用 [ACS 官方简化示例](https://www.overleaf.com/latex/templates/latex-template-for-american-chemical-society-acs-journal-submissions/swszwgfqsshj)支持的标准 `article` 与 `achemso` / BibTeX 组合，复用现有 ACS 构建；主文为单一 TeX，不复刻成刊双栏版式。骨架及示例由 Prism 原创，初始化离线完成，ACS 宏包由 TeX 发行版提供。

2026-11-08 核对 [Chemical Reviews 作者指南](https://researcher-resources.acs.org/publish/author_guidelines?coden=chreay)：综述须受邀或先提交提案并获得批准。模板提示英文摘要为 100–200 词单段，正文包含目录及 `1 / 1.1 / 1.1.1` 编号章节；引言交代综述范围和文献年份，主题正文侧重批判性比较、挑战与未来方向。目录默认显示前两级。每位作者的短简介、声明和可选缩写表均由作者补充，模板不虚构履历、检索经历或文献结论，也不代填或提交官方提案。

末页提供 **5×5 cm** 的 TOC 图占位，应替换为作者自己的原创图。独立 `supplementary.tex` 的 S1 页包含标题、作者和目录，后续页码、图、表和公式采用 S 编号；正文的 Supporting Information 段填写实际文件内容及格式。补充材料与 `examples.tex` 分别使用 `--main supplementary.tex --no-build-script`、`--main examples.tex --no-build-script` 构建，保留主文重建入口。默认中英混排用于写作；初始化加 `--language english` 使用英文 pdfLaTeX 模式，不自动翻译。

引用按首次出现顺序编号，正文使用无括号上标，文后编号加圆括号；显式保留完整文章标题，超过十位作者列前十位加 et al.，并显示可点击的 DOI。英文条目的 Title Case、CASSI 期刊缩写及页码须由作者准确提供，系统不自动改写或补查。示例文献仅用于验证引用机制，图表与数值均为合成排版素材，投稿前须替换。

## NAR

2026-11-06 核对：[Nucleic Acids Research 作者指南](https://academic.oup.com/nar/pages/author-guidelines)推荐 OUP **Modern Large**。`nar` 的三种原创正文共用仓库内的 OUP 1.5 class，不修改官方 class，不需要在线下载。省略 `--article-type` 时创建 research；`database` 侧重数据内容、整理、查询与更新，`web-server` 侧重输入输出、方法、验证和应用实例。这些小节是 Prism 的写作骨架，作者按实际研究调整。

英文摘要为单段、至多 200 词：常规稿不放 URL，Database/Web Server 稿必须给资源 URL。Methods 放在 Results 前；正文嵌入图表，提供页码，不启用行号。保留数据与代码可用性及其他声明占位，替换所有示例。中英混排用于写作；英文投稿稿可用 `--language english` 创建。

三类都提供独立 `graphical_abstract.tex`：5:2 横向合成占位，无图注，须换成作者自己的图。初投需单独上传图文摘要和补充材料；完整主文可提交 PDF，修回需可编辑源文件。`supplementary.tex` 使用 S 编号，这是 Prism 的约定。正文包含补充材料引用和声明；没有补充材料时应一并删去。

`prism-nar.bst` 从 OUP 包内的 `oup-plain.bst` 改名维护，并非官方 NAR 专用样式；完整保留原作者的改名修改授权，Prism 修改部分采用 LPPL 1.3c 或更新版本。它按首次引用顺序编号，保留文章标题，四人及以上列前三名加 et al.；`doi` 生成 DOI 链接，`pmcid` 优先生成 PMC 链接，没有 `pmcid` 时使用 `pmid`。请提供准确的英文元数据和期刊缩写；系统不自动查补文献。Web Server 稿按其指南提供可用的 DOI 与 PMC／PubMed 链接。

[Database 指南](https://academic.oup.com/nar/pages/Ms_Prep_Database)要求先提供可访问的资源和提案，取得邀请后投稿；更新稿说明实质变化。[Web Server 指南](https://academic.oup.com/nar/pages/Submission_Webserver)同样要求先提案并获得邀请，需说明输入输出、比较和验证。从 2026 年 11 月起全年接收提案，获准后两个月内交稿；不沿用旧年度截止日。这里提供写作和编译支持，不自动生成提案、投稿包或提交稿件。

## Angew

`angew` / `journal/angewandte-chemie-international-edition` 是 Prism 维护的四类写作草稿，不是 Angew 当前指定的官方模板。底稿来自 [Wiley／Overleaf 2019 通用模板](https://www.overleaf.com/latex/templates/wiley-journal-template/nnjcnfyhzcqp)，发布页标明 CC BY 4.0，也明确它已停止官方支持。原始 `wiley-article.cls` v1.5（2018-07-05）按[固定公开提交](https://github.com/ihrke/markdown-paper/blob/9d58a2550e43b1f6f797417fe4c5fc82d6e0e0bf/templates/dependencies/wiley-article.cls)和 SHA-256 保存于上游资源区，保留原字节；镜像仓库自身的许可不替代原作者授权。

改名的 `prism-wiley-article.cls` 保留署名及 CC BY 4.0，说明 Prism 的维护修改：按 TeX 字体文件名加载原有 Termes、XITS Math、Lato，修复摘要重复构造产生的未解析标签和段首溢出，并采用不拉伸短页的双栏预览。中英混排仅叠加中文字体，不替换该 class 的英文与数学字体。默认 XeLaTeX；创建时加 `--language english` 使用 pdfLaTeX。两种模式均不翻译正文。

2026-11-07 核对[Angew 作者指南](https://onlinelibrary.wiley.com/page/journal/15213773/homepage/notice-to-authors)：Research Article 使用 Introduction、Results and Discussion、Conclusion；Communication 正文连续叙述，不划分研究章节。两类通常分别约 5000／2500 词。Review 和 Minireview 使用编号主题章节并以 Summary and Outlook 结束，正文上限分别为 12000／5000 词；摘要最多 200 词。字数在占位说明中提示，不由 `--strict` 自动判断。

Review／Minireview 应先通过官网提交综述提案。本模板不提交提案或生成官方申请表。作者简介与肖像仅为占位，不引用任何真实个人照片；按官网快捷清单与详细 Review 段的交集，提示简介 70–84 词且不超过 560 字符（含空格），投稿前复核最新要求。综述补充材料仅提供额外比较与资料说明，不预填实验或宣称做过系统检索。

四类主文末页包含 TOC 图文占位：文本不超过 50 词且不超过 450 字符（含空格），最多五个字母序关键词，其中至少两个选自官方关键词目录。横图采用 11.0×2.5 cm，以同时满足作者指南及[图形指南](https://onlinelibrary.wiley.com/page/journal/15213773/homepage/graphics-guidelines)的尺寸说明。图表、Scheme、化学式和单位演示都是合成排版示例，应替换为实际研究内容。

独立 `supplementary.tex` 首页提供目录，按稿型组织实验、计算、表征或额外比较资料；图、表、Scheme、公式使用 S 编号。补充材料文献可独立从 1 编号，主文 Supporting Information 段演示如何纳入补充文献。`prism-angew.bst` 沿用 Prism 已有引用适配的授权基础，保留原始条款与 Prism 修改的 LPPL 声明；按引用顺序列完整文章标题和期刊名称，六人以内全列，超过六人列前三名加 et al.，支持 DOI 与文章编号。文内使用指南第 3.5 节说明的顺序方括号；出版前由期刊转换排版，不声称精确复刻最终成刊样式。

所有初始化资源已随仓库提供，创建时不下载或检查更新。保留英文参考文献和声明占位，替换作者、头像及示例后再准备投稿材料；本轮不进行 Word／RTF 转换、最终投稿打包或上传。

## 其他高质量官方模板

以下为精选参考入口，本版本没有将它们注册为可初始化选项，也没有承诺在 Prism 中完成编译验证。

| 家族 | 适合场景 | 来源与注意事项 |
| --- | --- | --- |
| Elsevier `elsarticle` / CAS | Elsevier 期刊，含单双栏结构 | [elsarticle](https://ctan.org/pkg/elsarticle)、[CAS](https://ctan.org/pkg/els-cas-templates)；LPPL。按目标期刊选择 class，不自动替换现有稿件 |
| IEEEtran | 工程、电子、计算机期刊与会议 | [官方 CTAN 包](https://ctan.org/pkg/ieeetran)；LPPL。采用目标 venue 指定配置，稳定版本的更新时间不代表使用价值低 |
| ACM `acmart` | ACM 期刊与会议 | [官方 CTAN 包](https://ctan.org/pkg/acmart)；LPPL。生产稿使用正式发布版，格式参数由 venue 决定 |
| REVTeX | APS / AIP 等物理论文 | [APS 官方入口](https://journals.aps.org/revtex)、[CTAN](https://ctan.org/pkg/revtex)；LPPL。保留 class 的引用与版式规则 |

模板质量以官方来源、许可清晰、数学与图表能力和可重建性判断，不只看成刊视觉效果。接入更多模板时先在临时目录验证，再标记为支持；不从历史研究目录回收未知版本的第三方文件。

## 维护上游版本

原创 demo 与上游文件分开维护。`skills/paper-latex/assets/upstream/manifest.json` 记录逐文件来源、版本、大小及 SHA-256；LICENSE 和 NOTICE 随所需文件复制到新项目。上游文件不适用 Prism 的 MIT 许可。

更新时由维护者从官方来源取得新版本，检查许可，保留原字节和署名，更新 manifest 及已审核版权文件的导出哈希，再运行测试、严格编译并检查页面后随 Prism 发布。用户创建或编译项目时不自动检查或下载更新。官方示例图和 PDF 不进入仓库；生成的论文也不会随模板升级被改写。
