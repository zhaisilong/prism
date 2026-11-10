# Briefings in Bioinformatics

BIB 使用 [OUP 作者模板](https://ctan.org/pkg/oup-authoring-template) 1.5（2026-07-14），采用 `unnumsec,webpdf,contemporary,large`，使用该版本默认的数字引用；旧期刊配置表中的 `numbered` 在新版 class 中会干扰编号，因此省略。初始化验证并复制仓库内固定版本的 class 和版权文件；高级用法仍可用 `--template-source` 导入固定官方 ZIP。主文为官方双栏，独立补充材料使用标准 `article` 单栏；参考文献使用 `unsrt` 按首次引用顺序编号。最终格式以 [BIB 作者指南](https://academic.oup.com/bib/pages/author-guidelines)和 [OUP 模板说明](https://academic.oup.com/pages/for-authors/journals/preparing-and-submitting-your-manuscript)为准。上游文件以原始许可公开，源码、README、上游 manifest 和删减说明集中保存在 `assets/upstream/oup/1.5/`。

独立示例可用 `scripts/latex-paper.sh PROJECT --main examples.tex --no-build-script` 构建。模板负责写作与编译支持；投稿前由作者核对当前期刊指南，字数、提案和投稿规则不属于自动合规检查。

[返回模板目录](../templates.md) · [日常使用](../guide.zh-CN.md) · [高级用法](../reference.zh-CN.md)
