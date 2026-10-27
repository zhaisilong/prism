# 三步写论文

也可以直接告诉 Codex：

> 用 $paper-latex 的 Nature 模板创建论文，放在 `projects/Papers/my-paper`，并编译。

第一次使用先在完整仓库中运行 `python3 scripts/install-paper-skill.py` 安装入口。

自己操作时，在 Prism 根目录完成下面三步。

## 1. 选模板并创建

| 模板 | 适合 |
| --- | --- |
| `nature` | Nature / NMI 英文初稿 |
| `nature-communications` | Nature Communications 研究论文 |
| `bib` | Briefings in Bioinformatics 英文稿 |
| `ddt` | Drug Discovery Today 单栏综述 |
| `jcim` | Journal of Chemical Information and Modeling 研究论文 |
| `jacs` | Journal of the American Chemical Society 研究论文 |
| `bioinformatics` | Bioinformatics 研究论文 |
| `science-advances` | Science Advances 研究论文 |
| `prism` | 通用论文、中英混排 |

```bash
scripts/latex-paper.sh --init projects/Papers/my-paper --template nature
```

更换模板时，把 `nature` 换成表格中的标识。全部模板均可离线创建。Nature 默认是我们维护的标准 `article` 初稿；官方版式见[高级用法](reference.zh-CN.md)。运行 `scripts/latex-paper.sh --list-templates` 查看完整名称；例如 `journal/jacs` 与 `jacs` 等价。

## 2. 写内容

打开项目文件夹，修改：

- `main.tex`：标题、作者和正文；Prism 模板的正文在 `sections/`。
- `references.bib`：参考文献。
- `supplementary.tex`：补充材料，需要时再写；Science Advances 的补充材料在 `main.tex` 中。

图表公式可参考 `examples.tex`。模板里的示例文字和数据在正式使用前替换。

## 3. 生成 PDF

```bash
scripts/latex-paper.sh projects/Papers/my-paper
```

打开项目文件夹里的 `main.pdf`。修改后重复这一步即可。

更多操作交给 Codex，例如：“编译补充材料”“把宽表排得更清楚”“修复编译报错”。官方模板导入、笔记、review 和排错见[高级用法](reference.zh-CN.md)。
