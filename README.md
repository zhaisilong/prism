# Prism LaTeX

用 LaTeX 写论文、整理笔记和排版审稿意见。

## 安装论文 skill

```bash
git clone https://github.com/zhaisilong/prism.git
python3 prism/scripts/install-paper-skill.py
```

已有完整仓库时，在根目录运行 `python3 scripts/install-paper-skill.py` 即可安装或更新入口。模板随仓库提供，创建论文无需下载官方包。编译需要 Python 3.9+、TeX Live 和 `latexmk`。

## 直接让 Codex 帮你

> 用 $paper-latex 的 Nature 模板创建一篇论文，放在 `projects/Papers/my-paper`，并编译检查。

已有论文时，告诉 Codex 文件位置和需要修改的内容即可。

## 自己运行

在 Prism 根目录执行：

```bash
scripts/latex-paper.sh --init projects/Papers/my-paper --template nature
scripts/latex-paper.sh projects/Papers/my-paper
```

修改 `main.tex` 和 `references.bib`，再次运行第二条命令更新 PDF。

- `nature`：Nature / NMI 英文初稿，使用我们维护的标准 `article` 模板。
- `nature-communications`：Nature Communications 研究论文草稿，可离线创建。
- `bib`：Briefings in Bioinformatics 英文稿；将命令中的 `nature` 换成 `bib` 即可。
- `ddt`：Drug Discovery Today 单栏综述；将 `nature` 换成 `ddt` 即可，可离线创建。
- `jcim`：Journal of Chemical Information and Modeling 研究论文，可离线创建。
- `jacs`：Journal of the American Chemical Society 研究论文，可离线创建。
- `bioinformatics`：Bioinformatics 研究论文。
- `science-advances`：Science Advances 研究论文，含连续编号的正文与补充文献。
- `prism`：通用科研草稿，支持中英混排。

以上模板均可离线创建，自动选择编译引擎。Nature 官方 `sn-jnl` 版式仍可通过高级本地导入使用，已有项目保持兼容。

使用 `scripts/latex-paper.sh --list-templates` 查看按类型分类的完整名称；例如 `journal/jacs` 与 `jacs` 等价。现有短名称继续可用。

[简明使用指南](docs/guide.zh-CN.md) · [模板来源](docs/templates.md) · [高级用法](docs/reference.zh-CN.md)

从 GitHub 克隆的副本可用 `git pull --ff-only` 更新模板与实现；仓库移动后重新运行安装命令。研究内容放在 `projects/`，公开同步时排除研究内容。同步方式见[维护说明](docs/public-sync.md)。版本以 `VERSION` 为准，采用日期版本。

Prism 自有代码与模板采用 [MIT License](LICENSE)；期刊模板使用的官方文件保留上游许可。开发维护规则见 [AGENTS.md](AGENTS.md)。
