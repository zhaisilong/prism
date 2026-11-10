# Journal of Medicinal Chemistry

`jmc` / `journal/journal-of-medicinal-chemistry` 提供 `research`（默认）和 `perspective` 两类 Prism 原创草稿。JMC 不强制指定模板；这里采用 `article` 与发行版中的 `achemso` / BibTeX，Letter、12 pt、1 英寸页边距、单栏双倍行距，正文标题不编号。初始化离线完成，默认 XeLaTeX 支持中英混排；`--language english` 使用 pdfLaTeX。中文支持只补充中文字体，不自动翻译，也不替换英文和数学排版。

```bash
scripts/latex-paper.sh --init projects/Papers/my-jmc --template jmc
scripts/latex-paper.sh --init projects/Papers/my-perspective --template jmc --article-type perspective
```

2026-11-08 核对 [JMC 作者指南](https://researcher-resources.acs.org/publish/author_guidelines?coden=jmcmar)。Research 的正文为 Introduction、Results and Discussion、Conclusion、Experimental；全部目标化合物的合成步骤应写在正文 Experimental，不能只放 SI。纯度、表征、实际测试条件、误差、重复次数及适用的伦理声明由作者据实填写，模板不预填已经满足纯度要求的断言。SMILES 与关联数据附件等投稿要求见官方指南，本轮不自动生成数据表或投稿包。

JMC 的综述型写作采用官方 **Perspective** 名称：围绕主题提供教学要点、批判性比较、局限和未来方向，而不是预填全面检索经历。通常由编辑邀请，主动投稿建议先与编辑沟通。两类摘要提示约 150 词；Perspective 在参考文献前提供每位作者少于 125 词的简介占位，应填写真实经历。官方主指南与链接的历史 Perspective 文档存在不同的篇幅提示，本草稿不固化页数或参考文献数限制。

两类主文末页均有标注 **Table of Contents graphic** 的 **80×42 mm** 图框，符合 [ACS TOC 图形指南](https://pubsapp.acs.org/paragonplus/submission/toc_abstract_graphics_guidelines.pdf)的最大区域内留白设计；替换为作者自己的原创图，并检查最终尺寸下的标识清晰度。正文提供合成 Scheme、化学式、SAR 表、带误差数值和图表公式交叉引用，全部只是排版演示。

引用按首次出现顺序编号，正文采用上标，显示完整文章标题及可点击 DOI。显式采用 `achemso` 的默认作者截断策略：15 人以内全列，超过 15 人列第一位加 et al.；这是本草稿的引用配置，不是自动判断期刊合规的规则。期刊缩写、标题和其他英文条目信息由作者准确提供。构建继续隔离 ACS 控制文件，避免覆盖或误读正文目录中的同名 `.bib`。

独立 `supplementary.tex` 首页包含标题、作者和目录，页码、图、表、Scheme 和公式使用 S 编号。使用 `scripts/latex-paper.sh PROJECT --main supplementary.tex --no-build-script`；共享 `examples.tex` 同样指定 `--main examples.tex --no-build-script`，保留主文重建入口。SI 只填写实际附带内容，不虚构实验或综述工作。

模板提供写作和可重建 PDF 支持；严格编译不认证字数、编辑邀请、数据质量或最终投稿要求。

[返回模板目录](../templates.md) · [日常使用](../guide.zh-CN.md) · [高级用法](../reference.zh-CN.md)
