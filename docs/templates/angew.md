# Angew

`angew` / `journal/angewandte-chemie-international-edition` 是 Prism 维护的四类写作草稿，不是 Angew 当前指定的官方模板。底稿来自 [Wiley／Overleaf 2019 通用模板](https://www.overleaf.com/latex/templates/wiley-journal-template/nnjcnfyhzcqp)，发布页标明 CC BY 4.0，也明确它已停止官方支持。原始 `wiley-article.cls` v1.5（2018-07-05）按[固定公开提交](https://github.com/ihrke/markdown-paper/blob/9d58a2550e43b1f6f797417fe4c5fc82d6e0e0bf/templates/dependencies/wiley-article.cls)和 SHA-256 保存于上游资源区，保留原字节；镜像仓库自身的许可不替代原作者授权。

改名的 `prism-wiley-article.cls` 保留署名及 CC BY 4.0，说明 Prism 的维护修改：按 TeX 字体文件名加载原有 Termes、XITS Math、Lato，修复摘要重复构造产生的未解析标签和段首溢出，并采用不拉伸短页的双栏预览。中英混排仅叠加中文字体，不替换该 class 的英文与数学字体。默认 XeLaTeX；创建时加 `--language english` 使用 pdfLaTeX。两种模式均不翻译正文。

2026-11-07 核对[Angew 作者指南](https://onlinelibrary.wiley.com/page/journal/15213773/homepage/notice-to-authors)：Research Article 使用 Introduction、Results and Discussion、Conclusion；Communication 正文连续叙述，不划分研究章节。两类通常分别约 5000／2500 词。Review 和 Minireview 使用编号主题章节并以 Summary and Outlook 结束，正文上限分别为 12000／5000 词；摘要最多 200 词。字数在占位说明中提示，不由 `--strict` 自动判断。

Review／Minireview 应先通过官网提交综述提案。本模板不提交提案或生成官方申请表。作者简介与肖像仅为占位，不引用任何真实个人照片；按官网快捷清单与详细 Review 段的交集，提示简介 70–84 词且不超过 560 字符（含空格），投稿前复核最新要求。综述补充材料仅提供额外比较与资料说明，不预填实验或宣称做过系统检索。

四类主文末页包含 TOC 图文占位：文本不超过 50 词且不超过 450 字符（含空格），最多五个字母序关键词，其中至少两个选自官方关键词目录。横图采用 11.0×2.5 cm，以同时满足作者指南及[图形指南](https://onlinelibrary.wiley.com/page/journal/15213773/homepage/graphics-guidelines)的尺寸说明。图表、Scheme、化学式和单位演示都是合成排版示例，应替换为实际研究内容。

独立 `supplementary.tex` 首页提供目录，按稿型组织实验、计算、表征或额外比较资料；图、表、Scheme、公式使用 S 编号。补充材料文献可独立从 1 编号，主文 Supporting Information 段演示如何纳入补充文献。`prism-angew.bst` 沿用 Prism 已有引用适配的授权基础，保留原始条款与 Prism 修改的 LPPL 声明；按引用顺序列完整文章标题和期刊名称，六人以内全列，超过六人列前三名加 et al.，支持 DOI 与文章编号。文内使用指南第 3.5 节说明的顺序方括号；出版前由期刊转换排版，不声称精确复刻最终成刊样式。

所有初始化资源已随仓库提供，创建时不下载或检查更新。保留英文参考文献和声明占位，替换作者、头像及示例后再准备投稿材料；本轮不进行 Word／RTF 转换、最终投稿打包或上传。

独立示例可用 `scripts/latex-paper.sh PROJECT --main examples.tex --no-build-script` 构建。模板负责写作与编译支持；投稿前由作者核对当前期刊指南，字数、提案和投稿规则不属于自动合规检查。

[返回模板目录](../templates.md) · [日常使用](../guide.zh-CN.md) · [高级用法](../reference.zh-CN.md)
