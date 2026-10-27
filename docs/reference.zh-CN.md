# 高级用法与排错

日常使用只需[三步指南](guide.zh-CN.md)。下面保留离线导入、补充材料、排错与维护细节，按需查阅。

## 1. 从一篇论文开始

```bash
scripts/latex-paper.sh --version
scripts/latex-paper.sh --list-templates
scripts/latex-paper.sh --check-deps
scripts/latex-paper.sh --init projects/Papers/my-paper --template prism
scripts/latex-paper.sh projects/Papers/my-paper --strict
```

默认 `prism` 模板使用 `article`，适合英文或中英混排草稿。修改 `main.tex` 的作者信息、`sections/` 的正文和 `references.bib` 的文献。初始化目录非空时会停止；只有明确使用 `--force` 才会把原目录整体备份后替换。

图表公式示例集中在 `examples.tex`，便于复制所需片段，不必让正式正文承载全部演示：

```bash
scripts/latex-paper.sh projects/Papers/my-paper \
  --main examples.tex --strict --no-build-script
scripts/latex-paper.sh projects/Papers/my-paper \
  --main supplementary.tex --strict --no-build-script
```

这些命令分别生成 `examples.pdf`、`supplementary.pdf`。补充材料使用 S 编号；它的引用独立解析，不自动继承主文计数。`--no-build-script` 保留主文的重建入口。

## 2. 使用 Nature / NMI 模板

```bash
scripts/latex-paper.sh --init projects/Papers/nmi-paper --template nature
scripts/latex-paper.sh projects/Papers/nmi-paper --check-deps
scripts/latex-paper.sh projects/Papers/nmi-paper --strict
```

默认初始化使用 Prism 维护的标准 `article` 初稿，无需联网。主文、参考文献和独立补充材料分别在 `main.tex`、`references.bib`、`supplementary.tex`；使用 pdfLaTeX 与 BibTeX。已有 `sn-jnl` 项目继续使用原资源，不会自动转换。

需要官方 `sn-jnl` / `sn-nature` 版式时，从[官方作者支持页](https://www.springernature.com/gp/authors/campaigns/latex-author-support)取得[固定版本原始 ZIP](https://cms-resources.apps.public.k8s.springernature.io/springer-cms/rest/v1/content/18782940/data/v12)，显式导入到新目录：

```bash
scripts/latex-paper.sh --init projects/Papers/nmi-official --template nature \
  --template-source path/to/official-template.zip
```

导入只读取本地文件，不自动下载。原始 ZIP 的 SHA-256 必须匹配，重新打包或 Overleaf 导出不等同于该原包；失败不会覆盖目标。官方 ZIP、class 和样式留在生成的本地项目中，保留上游许可。官方 class 已设置 bibliography style，不重复加载 `natbib` 或 Prism 字体版式。

NMI 初稿接受编译后的 PDF，通常无需模仿成刊版面。接收后的 TeX 要求另外整理单一源文件、字体和内嵌参考文献；本版本没有自动完成最终投稿导出。不同文章类型的字数和图表数以当前官方要求为准，额外实验与大表可组织到补充材料。参见 [NMI 初稿要求](https://www.nature.com/natmachintell/submission-guidelines/initial-formatting)、[内容类型](https://www.nature.com/natmachintell/content)及[最终格式要求](https://www.nature.com/natmachintell/submission-guidelines/aip-and-formatting)。核查日期：2026-10-24。

## 3. Briefings in Bioinformatics（BIB）

```bash
scripts/latex-paper.sh --init projects/Papers/bib-paper --template bib
scripts/latex-paper.sh projects/Papers/bib-paper --strict
```

正文使用官方 OUP 双栏配置；宽图与宽表使用 `figure*`、`table*`，跨页长表放入单栏的 `supplementary.tex`。正文、参考文献和补充材料分别修改 `main.tex`、`references.bib`、`supplementary.tex`。

默认从仓库复制固定 OUP 文件，无需联网。需要显式导入时可用 `--template-source path/to/oup-authoring-template.zip`，仍按固定原始 ZIP 校验。补充材料用 `--main supplementary.tex --no-build-script` 单独编译。来源与配置见[模板选型](templates.md)。

## 4. Drug Discovery Today（DDT）

```bash
scripts/latex-paper.sh --init projects/Papers/ddt-review --template ddt
scripts/latex-paper.sh projects/Papers/ddt-review --strict
```

这是单栏叙述性综述草稿；`highlights.txt` 和 `teaser.txt` 是可选占位，按期刊当时要求编辑。使用已安装的 Elsevier `elsarticle` 和 BibTeX；缺少依赖时运行 `scripts/latex-paper.sh projects/Papers/ddt-review --check-deps`。补充材料使用 `--main supplementary.tex --no-build-script` 单独编译。投稿要求与官方来源见[模板选型](templates.md)。

## 5. 图片、表格与公式较多时

- 图片优先用矢量 PDF；照片等位图保持合适分辨率。用 `width=\linewidth,keepaspectratio` 控制尺寸，给长图注留出页面空间。论文字体设置不能改变图片内部的轴标签字体。
- 多面板图使用统一字号和清晰的 a/b/c 标签；在正文按首次出现顺序引用。图注说明已有的单位、误差和样本量，排版过程不补造科研信息。
- 表格先调整列宽、换行表头或拆分内容，再考虑横向页面。数值与误差用 `siunitx` 对齐；跨页表用 `longtable` 的重复表头，不把它嵌套在浮动体中。
- 多行公式用 `align` / `split`，分段函数用 `cases`，相关公式用 `subequations`。使用 `\label`、`\ref`、`\eqref`，避免手写序号。
- `prism` 的默认正文保持中英混排；`nature` 默认为标准 `article` 英文初稿，显式官方模式保留其 class 配置。不要把草稿字体配置直接套在期刊 class 上。

可复制的完整演示见模板中的 `examples.tex`；详细排版建议见 [layout guidance](../skills/paper-latex/references/layout.md)。示例数据明确为合成内容，正式交付前全部替换。

## 6. 笔记和已有 review

```bash
scripts/latex-note.sh projects/Notes/note.md --strict
scripts/latex-review.sh projects/Reviews/Others/draft.md \
  --journal "Example Journal" --review-id "DEMO-001" \
  --title "Example manuscript" --decision "Major Revision" --strict
```

review 的编辑备注只出现在独立的 `_editor_notes.pdf` 中。交付前分别核对作者版和编辑版。`--outdir` 选择输出目录，`--out` 优先指定作者版路径。仅导出 TeX 可使用 `--no-compile`，无需 LaTeX 编译器；DOCX 输入可选依赖 `python-docx`，文本型 PDF 可用 `pypdf` 或 `pdftotext`。

## 7. 重建、排错和在 Codex 中使用

主文成功构建后：

```bash
cd projects/Papers/my-paper
./prism-build.sh
```

脚本记录输入、输出和有效参数，并在本地查找 Prism。仓库移动后可用 `PRISM_PROJECT_DIR` 指向新位置，或重新运行安装器；不要从全局 skill 寻找本项目的实现。

| 遇到的问题 | 处理方式 |
| --- | --- |
| 找不到编译器或宏包 | 运行对应 wrapper 的 `--check-deps`；按报告补齐 TeX Live 依赖 |
| 官方 Nature 项目缺少 class/BST | 用匹配的官方包在新目录初始化，再检查需要的原文件；不要覆盖原论文 |
| `??` 引用或 citation 未定义 | 检查 label、引用键、`.bib` 与文献路径；由 `latexmk` 完成所需轮次 |
| 宽表或公式越界 | 调整换行、列宽或公式分行，重新运行 `--strict` 并检查 PDF |
| 编译失败需要日志 | 加 `--keep-work` 重试，查看打印出的临时目录；旧 PDF 保留 |
| 已有 `prism-build.sh` 未被替换 | 检查是否为自有脚本；明确需要替换时用 `--force-build-script`，原文件会备份 |

可向 Codex 提出：“使用本仓库的 paper-latex，为我初始化 Nature 模板，并编译检查主文和补充材料”；或“按 layout guidance 调整这张宽表，保持全部数值与结论”。桌面原生编辑器支持本地多文件项目；使用根 wrapper 获得这里约定的临时构建、严格检查和重建脚本。

日期版本见根目录 `VERSION`。公开同步前请遵循[独立代码导出流程](public-sync.md)，不要直接推送原仓库历史。

## 8. 安装与更新 paper-latex

从完整仓库运行 `python3 scripts/install-paper-skill.py`。不要只下载 `skills/paper-latex/`，它需要仓库共享实现。安装器优先更新已有 Prism 入口；新装默认使用 `~/.agents/skills/paper-latex`，也可用 `--skills-dir PATH` 指定其他 skills 目录。新入口保持自动调用；未显示时重启 Codex。目录发现行为参见 [OpenAI Docs](https://learn.chatgpt.com/docs/build-skills)。

安装器只修改 paper-latex，先把旧目录备份到 skills 目录外的 `prism-skill-backups`；重复安装同一入口不重复备份。非 Prism 同名 skill 或改过的入口需显式 `--force` 才会备份替换；符号链接、重叠路径和并发变化会停止。安装器输出的本机路径和备份留在本地，不进入公开导出。

从 GitHub 克隆的代码副本可运行 `git pull --ff-only` 更新模板；原本的研究 checkout 继续使用独立代码导出流程。安装后的入口始终指向当前仓库，不另存模板副本。迁移仓库后重新运行安装器即可更新路径。
