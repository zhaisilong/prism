# Chemical Reviews

`chemrev` / `journal/chemical-reviews` 提供 Prism 维护的常规 Review 草稿，暂不包含 Focus Review。创建时直接选择 `--template chemrev`，不使用 `--article-type`。采用 [ACS 官方简化示例](https://www.overleaf.com/latex/templates/latex-template-for-american-chemical-society-acs-journal-submissions/swszwgfqsshj)支持的标准 `article` 与 `achemso` / BibTeX 组合，复用现有 ACS 构建；主文为单一 TeX，不复刻成刊双栏版式。骨架及示例由 Prism 原创，初始化离线完成，ACS 宏包由 TeX 发行版提供。

2026-11-08 核对 [Chemical Reviews 作者指南](https://researcher-resources.acs.org/publish/author_guidelines?coden=chreay)：综述须受邀或先提交提案并获得批准。模板提示英文摘要为 100–200 词单段，正文包含目录及 `1 / 1.1 / 1.1.1` 编号章节；引言交代综述范围和文献年份，主题正文侧重批判性比较、挑战与未来方向。目录默认显示前两级。每位作者的短简介、声明和可选缩写表均由作者补充，模板不虚构履历、检索经历或文献结论，也不代填或提交官方提案。

末页提供 **5×5 cm** 的 TOC 图占位，应替换为作者自己的原创图。独立 `supplementary.tex` 的 S1 页包含标题、作者和目录，后续页码、图、表和公式采用 S 编号；正文的 Supporting Information 段填写实际文件内容及格式。补充材料与 `examples.tex` 分别使用 `--main supplementary.tex --no-build-script`、`--main examples.tex --no-build-script` 构建，保留主文重建入口。默认中英混排用于写作；初始化加 `--language english` 使用英文 pdfLaTeX 模式，不自动翻译。

引用按首次出现顺序编号，正文使用无括号上标，文后编号加圆括号；显式保留完整文章标题，超过十位作者列前十位加 et al.，并显示可点击的 DOI。英文条目的 Title Case、CASSI 期刊缩写及页码须由作者准确提供，系统不自动改写或补查。示例文献仅用于验证引用机制，图表与数值均为合成排版素材，投稿前须替换。

独立示例可用 `scripts/latex-paper.sh PROJECT --main examples.tex --no-build-script` 构建。模板负责写作与编译支持；投稿前由作者核对当前期刊指南，字数、提案和投稿规则不属于自动合规检查。

[返回模板目录](../templates.md) · [日常使用](../guide.zh-CN.md) · [高级用法](../reference.zh-CN.md)
