# Prism 通用模板

Prism 原创通用科研草稿，采用 MIT 许可。它借鉴期刊论文清晰的标题层次、图表和补充材料组织方式，采用便于写作与审阅的单栏版式，并非特定期刊的投稿模板。`main.tex` 加载 `sections/` 中的分节正文；默认支持中文和中英混排，英文与数学使用 Prism 的通用字体和尺寸。期刊模板保留各自版式，不应用这些通用设置。系统不会自动翻译或检查投稿合规性。

在 `main.tex` 中修改 `\papertitle`、`\runningtitle`、`\paperauthors`、机构、通讯作者和关键词等宏，并按实际作者和机构编辑元数据行。`sections/` 中分别填写摘要和正文，声明按事实填写，不适用的可删除。模板内容均为写作或排版示例，正式使用前请替换。

主文包含多面板图和表格示例；`examples.tex` 进一步展示长图注、宽表、重复表头长表、数值与误差对齐、多行公式和交叉引用。根据图注长度给图片留出空间，并检查图片内部文字在最终尺寸下是否清晰；示例数字均为合成内容。

使用 XeLaTeX 或 LuaLaTeX 和 BibTeX。独立的 `supplementary.tex` 含首页与目录，章节、图表、公式和页码采用 S 编号；在该文件中修改标题、作者及内容。补充材料使用 `placeins` 控制图表顺序，可通过 `--check-deps --template prism` 检查依赖。分别编译补充材料和示例时保留主文重建入口：

```bash
scripts/latex-paper.sh PROJECT --main supplementary.tex --no-build-script
scripts/latex-paper.sh PROJECT --main examples.tex --no-build-script
```

新版版面应用于新初始化的项目；已有项目不会自动更改。

[返回模板目录](../templates.md) · [日常使用](../guide.zh-CN.md) · [高级用法](../reference.zh-CN.md)
