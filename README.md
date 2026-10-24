# Prism LaTeX

用 LaTeX 写论文、整理笔记和排版审稿意见。

## 直接让 Codex 帮你

> 用 Nature 模板创建一篇论文，放在 `projects/Papers/my-paper`。图表和公式较多，请帮我编译检查。

已有论文时，告诉 Codex 文件位置和需要修改的内容即可。

## 自己运行

在 Prism 根目录执行：

```bash
scripts/latex-paper.sh --init projects/Papers/my-paper --template nature
scripts/latex-paper.sh projects/Papers/my-paper
```

修改 `main.tex` 和 `references.bib`，再次运行第二条命令更新 PDF。

- `nature`：Nature / NMI 英文初稿；首次创建需要联网。
- `prism`：通用科研草稿，支持中英混排。

需要 Python 3.9+、TeX Live 和 `latexmk`。模板会自动选择编译引擎。

[简明使用指南](docs/guide.zh-CN.md) · [模板来源](docs/templates.md) · [高级用法](docs/reference.zh-CN.md)

研究内容放在 `projects/`，代码公开同步时排除研究内容。同步方式见[维护说明](docs/public-sync.md)。版本以 `VERSION` 为准，采用日期版本。

Prism 自有代码与模板采用 [MIT License](LICENSE)；Nature 官方文件保留上游许可。开发维护规则见 [AGENTS.md](AGENTS.md)。
