# NAR

2026-11-06 核对：[Nucleic Acids Research 作者指南](https://academic.oup.com/nar/pages/author-guidelines)推荐 OUP **Modern Large**。`nar` 的三种原创正文共用仓库内的 OUP 1.5 class，不修改官方 class，不需要在线下载。省略 `--article-type` 时创建 research；`database` 侧重数据内容、整理、查询与更新，`web-server` 侧重输入输出、方法、验证和应用实例。这些小节是 Prism 的写作骨架，作者按实际研究调整。

英文摘要为单段、至多 200 词：常规稿不放 URL，Database/Web Server 稿必须给资源 URL。Methods 放在 Results 前；正文嵌入图表，提供页码，不启用行号。保留数据与代码可用性及其他声明占位，替换所有示例。中英混排用于写作；英文投稿稿可用 `--language english` 创建。

三类都提供独立 `graphical_abstract.tex`：5:2 横向合成占位，无图注，须换成作者自己的图。初投需单独上传图文摘要和补充材料；完整主文可提交 PDF，修回需可编辑源文件。`supplementary.tex` 使用 S 编号，这是 Prism 的约定。正文包含补充材料引用和声明；没有补充材料时应一并删去。

`prism-nar.bst` 从 OUP 包内的 `oup-plain.bst` 改名维护，并非官方 NAR 专用样式；完整保留原作者的改名修改授权，Prism 修改部分采用 LPPL 1.3c 或更新版本。它按首次引用顺序编号，保留文章标题，四人及以上列前三名加 et al.；`doi` 生成 DOI 链接，`pmcid` 优先生成 PMC 链接，没有 `pmcid` 时使用 `pmid`。请提供准确的英文元数据和期刊缩写；系统不自动查补文献。Web Server 稿按其指南提供可用的 DOI 与 PMC／PubMed 链接。

[Database 指南](https://academic.oup.com/nar/pages/Ms_Prep_Database)要求先提供可访问的资源和提案，取得邀请后投稿；更新稿说明实质变化。[Web Server 指南](https://academic.oup.com/nar/pages/Submission_Webserver)同样要求先提案并获得邀请，需说明输入输出、比较和验证。从 2026 年 11 月起全年接收提案，获准后两个月内交稿；不沿用旧年度截止日。这里提供写作和编译支持，不自动生成提案、投稿包或提交稿件。

独立示例可用 `scripts/latex-paper.sh PROJECT --main examples.tex --no-build-script` 构建。模板负责写作与编译支持；投稿前由作者核对当前期刊指南，字数、提案和投稿规则不属于自动合规检查。

[返回模板目录](../templates.md) · [日常使用](../guide.zh-CN.md) · [高级用法](../reference.zh-CN.md)
