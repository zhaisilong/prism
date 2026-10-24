# 论文模板选型与来源

核查日期：2026-10-24。Prism 版本和上游模板版本分别记录；“可初始化”表示已提供接入流程，具体期刊的投稿要求仍以官网为准。

## 可直接初始化

| 标识 | 用途 | 引擎 / 文献 | 文件来源 |
| --- | --- | --- | --- |
| `prism`（默认） | 通用科研草稿、中英混排、复杂图表公式与补充材料 | XeLaTeX 或 LuaLaTeX / BibTeX | Prism 原创模板，MIT |
| `nature` | Nature Portfolio / NMI 初稿写作 | pdfLaTeX / BibTeX，`sn-nature` | Prism 原创启动文件 + 本地获取的官方 Springer Nature 3.1 文件 |

`prism` 的 `main.tex` 分节写作；`nature` 主文是单一 TeX，不加载 Prism 字体样式。两者均附 `examples.tex` 和独立 `supplementary.tex`；所有演示均为格式示例。

本版本已在临时目录严格编译两个模板的主文、补充材料和示例，检查代表页面；Prism 另通过 LuaLaTeX 构建。独立补充材料与示例使用 `--no-build-script` 保留主文重建入口。

Nature 官方包来自 [Springer Nature 作者支持页](https://www.springernature.com/gp/authors/campaigns/latex-author-support)，也可从[官方 Overleaf 模板](https://www.overleaf.com/latex/templates/springer-nature-latex-template/myxmhdsbzkyd)查看。接入实现固定下载地址、版本与 SHA-256，并保留下载的完整 ZIP。上游 class/BST 保留其许可，不纳入 Prism MIT，也不上传到公开代码库。

NMI 提供[初稿要求](https://www.nature.com/natmachintell/submission-guidelines/initial-formatting)和[接收后格式要求](https://www.nature.com/natmachintell/submission-guidelines/aip-and-formatting)。`sn-jnl` 是官方提供的可选方案；不要把它理解为 NMI 强制 class，或宣称本模板已完成最终投稿整理。

## 其他高质量官方模板

以下为精选参考入口，本版本没有将它们注册为可初始化选项，也没有承诺在 Prism 中完成编译验证。

| 家族 | 适合场景 | 来源与注意事项 |
| --- | --- | --- |
| Elsevier `elsarticle` / CAS | Elsevier 期刊，含单双栏结构 | [elsarticle](https://ctan.org/pkg/elsarticle)、[CAS](https://ctan.org/pkg/els-cas-templates)；LPPL。按目标期刊选择 class，不自动替换现有稿件 |
| IEEEtran | 工程、电子、计算机期刊与会议 | [官方 CTAN 包](https://ctan.org/pkg/ieeetran)；LPPL。采用目标 venue 指定配置，稳定版本的更新时间不代表使用价值低 |
| ACM `acmart` | ACM 期刊与会议 | [官方 CTAN 包](https://ctan.org/pkg/acmart)；LPPL。生产稿使用正式发布版，格式参数由 venue 决定 |
| REVTeX | APS / AIP 等物理论文 | [APS 官方入口](https://journals.aps.org/revtex)、[CTAN](https://ctan.org/pkg/revtex)；LPPL。保留 class 的引用与版式规则 |

模板质量以官方来源、许可清晰、数学与图表能力和可重建性判断，不只看成刊视觉效果。接入更多模板时先在临时目录验证，再标记为支持；不从历史研究目录回收未知版本的第三方文件。
