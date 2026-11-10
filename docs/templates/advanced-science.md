# Advanced Science

`advanced-science` / `journal/advanced-science` 面向 Wiley-VCH 的 Advanced Science，提供 `research`（默认）、`review` 和 `perspective` 三类原创骨架。它采用标准单栏 `article`：A4、11 pt、25 mm 页边距；中文模式只补充中文字体，保留英文与数学排版。初始化离线完成，默认 XeLaTeX；加 `--language english` 使用 pdfLaTeX，均通过 BibTeX 处理英文参考文献，不自动翻译。

2026-11-08 核对[官方作者指南](https://advanced.onlinelibrary.wiley.com/hub/journal/21983844/author-guidelines)后，按其首次 Free Format 和稿件内容要求维护写作草稿。[官方 LaTeX ZIP](https://advanced.onlinelibrary.wiley.com/pb-assets/assets/vch/msp/LaTeX-template-1782154981423.zip)在此次核查中返回 403，包内 class、字体及再分发许可尚未核实，因此仓库不镜像它，也不将 Angew 的历史双栏 class 用作本刊模板。本骨架不声称复刻官方 class 或最终成刊版式。

| 稿型 | 正文重点 |
| --- | --- |
| `research` | Introduction、Results and Discussion、Conclusion、Experimental/Methods；方法末尾提供 Statistical Analysis 占位，按真实研究填写 |
| `review` | 主题章节、批判性比较、知识缺口、Challenges and Outlook，不预填实验或检索经历 |
| `perspective` | 背景、核心观点与证据、争议或开放问题、未来方向 |

三类都提示摘要不超过 200 词、3–7 个关键词，并提供资助、利益冲突、数据可用性等声明占位；研究涉及伦理审批或知情同意时，填写已确认的信息。Review 可未经邀请直接投稿，Perspective 通常由编辑邀请。Review、Perspective 的主要作者肖像与简介属于可选内容，可删除相应占位；简介提示不超过 100 词，填写真实经历与研究兴趣，不罗列奖项、论文或专利数量。

主文末页提供 TOC 图文：文字提示为 50–60 词，面向一般读者，以第三人称概括实际内容；默认图框 **55×50 mm**，也可按注释改成 **110×20 mm**。替换为拥有版权的原创图。正文图、表、Scheme、公式均为合成排版示例；保持最终尺寸下的图中文字清晰，替换示例时保留实际数据、单位、标签与精度。

三类独立 `supplementary.tex` 的首页包含标题、作者和目录，按稿型安排方法细节、额外比较或论据说明。页码、图、表、Scheme 和公式采用 S 编号，这是 Prism 的写作约定。用 `--main supplementary.tex --no-build-script` 构建；共享图表公式参考使用 `--main examples.tex --no-build-script`，均保留主文重建入口。

`prism-wiley-numeric.bst` 基于 Prism 已有的授权适配维护通用数字引用，保留原始条款及 Prism 修改部分的 LPPL 1.3c 或更新版本声明。文内采用当前网页规定的行内方括号，按首次引用顺序编号；每个编号对应一篇文献，保留完整文章标题、期刊名称和 DOI 链接。六位以内作者全列，超过六位列前三位加 et al.；请提供准确的英文条目，系统不自动查补。该样式用于一致的草稿引用，最终文献排版由期刊处理；Angew 的原有引用资源保持不变。

独立示例可用 `scripts/latex-paper.sh PROJECT --main examples.tex --no-build-script` 构建。模板负责写作与编译支持；投稿前由作者核对当前期刊指南，字数、提案和投稿规则不属于自动合规检查。

[返回模板目录](../templates.md) · [日常使用](../guide.zh-CN.md) · [高级用法](../reference.zh-CN.md)
