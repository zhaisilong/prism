# 论文模板选型与来源

按投稿目标选择模板，再阅读对应的详细说明。Prism 版本与上游版本分别记录；可初始化表示已提供写作与构建支持，投稿要求仍以期刊当前指南为准。字数、提案和提交规则由维护者核对并记录，不由严格编译自动认证。

```bash
scripts/latex-templates.sh
scripts/latex-templates.sh --show advanced-science
scripts/latex-templates.sh --show advanced-science --json
```

## 可直接初始化

<!-- prism:template-catalog:start -->
| 标识 | 期刊 / 用途 | 出版社 | 稿型 |
| --- | --- | --- | --- |
| [`science-advances`](templates/science-advances.md) | Science Advances | AAAS | `research` |
| [`chemrev`](templates/chemrev.md) | Chemical Reviews | ACS | `review` |
| [`jcim`](templates/jcim.md) | Journal of Chemical Information and Modeling | ACS | `research` |
| [`jmc`](templates/jmc.md) | Journal of Medicinal Chemistry | ACS | `research`（默认）、`perspective` |
| [`jacs`](templates/jacs.md) | Journal of the American Chemical Society | ACS | `research` |
| [`ddt`](templates/ddt.md) | Drug Discovery Today | Elsevier | `review` |
| [`dyes`](templates/dyes.md) | Dyes and Pigments | Elsevier | `research`（默认）、`review` |
| [`ejmc`](templates/ejmc.md) | European Journal of Medicinal Chemistry | Elsevier | `research`（默认）、`review` |
| [`bioinformatics`](templates/bioinformatics.md) | Bioinformatics | Oxford University Press | `original` |
| [`bib`](templates/bib.md) | Briefings in Bioinformatics | Oxford University Press | `manuscript` |
| [`nar`](templates/nar.md) | Nucleic Acids Research | Oxford University Press | `research`（默认）、`database`、`web-server` |
| [`rsc-advances`](templates/rsc-advances.md) | RSC Advances | Royal Society of Chemistry | `research`（默认）、`review` |
| [`jcheminformatics`](templates/jcheminformatics.md) | Journal of Cheminformatics | Springer Nature | `research` |
| [`nature`](templates/nature.md) | Nature | Springer Nature | `research` |
| [`nature-communications`](templates/nature-communications.md) | Nature Communications | Springer Nature | `research` |
| [`nmi`](templates/nmi.md) | Nature Machine Intelligence | Springer Nature | `article`（默认）、`analysis`、`review` |
| [`nature-methods`](templates/nature-methods.md) | Nature Methods | Springer Nature | `article`（默认）、`resource`、`analysis` |
| [`advanced-science`](templates/advanced-science.md) | Advanced Science | Wiley-VCH | `research`（默认）、`review`、`perspective` |
| [`angew`](templates/angew.md) | Angewandte Chemie International Edition | Wiley-VCH | `research`（默认）、`communication`、`review`、`minireview` |
| [`prism`](templates/prism.md) | Prism | 通用 | `manuscript` |
<!-- prism:template-catalog:end -->

全部默认模板离线初始化，默认支持中文和中英混排；期刊模板使用 XeLaTeX，通用 `prism` 也支持 LuaLaTeX。创建期刊项目时可用 `--language english` 选择 pdfLaTeX；这不翻译文字，也不转换已有项目。参考文献目前使用英文条目。

期刊草稿以英文稿结构和版式为基础，中文支持仅补充中文字体，不叠加 Prism 通用英文与数学排版。各模板均附合成 `examples.tex`；Science Advances 在 `main.tex` 中合并补充材料，其余模板提供独立 `supplementary.tex`。独立材料和示例使用 `--no-build-script` 保留主文重建入口。

以下保留旧链接入口，详细规则按需阅读。

## Prism

见[Prism 通用模板说明](templates/prism.md)。

## Nature

见 [Nature 本刊模板说明](templates/nature.md)和 [Nature Machine Intelligence 模板说明](templates/nmi.md)。

## Nature Communications

见[Nature Communications 模板说明](templates/nature-communications.md)。

## BIB

见[Briefings in Bioinformatics 模板说明](templates/bib.md)。

## DDT

见[Drug Discovery Today 模板说明](templates/ddt.md)。

## JCIM

见[Journal of Chemical Information and Modeling 模板说明](templates/jcim.md)。

## Journal of Cheminformatics

见[Journal of Cheminformatics 模板说明](templates/jcheminformatics.md)。

## JACS

见[Journal of the American Chemical Society 模板说明](templates/jacs.md)。

## Bioinformatics

见[Bioinformatics 模板说明](templates/bioinformatics.md)。

## Science Advances

见[Science Advances 模板说明](templates/science-advances.md)。

## Chemical Reviews

见[Chemical Reviews 模板说明](templates/chemrev.md)。

## NAR

见[NAR 模板说明](templates/nar.md)。

## Angew

见[Angew 模板说明](templates/angew.md)。

## Advanced Science

见[Advanced Science 模板说明](templates/advanced-science.md)。

## JMC

见[Journal of Medicinal Chemistry 模板说明](templates/jmc.md)。

## EJMC

见[European Journal of Medicinal Chemistry 模板说明](templates/ejmc.md)。

## 其他高质量官方模板

以下为精选参考入口，本版本没有将它们注册为可初始化选项，也没有承诺在 Prism 中完成编译验证。

| 家族 | 适合场景 | 来源与注意事项 |
| --- | --- | --- |
| Elsevier `elsarticle` / CAS | Elsevier 期刊，含单双栏结构 | [elsarticle](https://ctan.org/pkg/elsarticle)、[CAS](https://ctan.org/pkg/els-cas-templates)；LPPL。按目标期刊选择 class，不自动替换现有稿件 |
| IEEEtran | 工程、电子、计算机期刊与会议 | [官方 CTAN 包](https://ctan.org/pkg/ieeetran)；LPPL。采用目标 venue 指定配置，稳定版本的更新时间不代表使用价值低 |
| ACM `acmart` | ACM 期刊与会议 | [官方 CTAN 包](https://ctan.org/pkg/acmart)；LPPL。生产稿使用正式发布版，格式参数由 venue 决定 |
| REVTeX | APS / AIP 等物理论文 | [APS 官方入口](https://journals.aps.org/revtex)、[CTAN](https://ctan.org/pkg/revtex)；LPPL。保留 class 的引用与版式规则 |

模板质量以官方来源、许可清晰、数学与图表能力和可重建性判断，不只看成刊视觉效果。接入更多模板时先在临时目录验证，再标记为支持；不从历史研究目录回收未知版本的第三方文件。

## 维护上游版本

原创 demo 与上游文件分开维护。`skills/paper-latex/assets/upstream/manifest.json` 记录逐文件来源、版本、大小及 SHA-256；LICENSE 和 NOTICE 随所需文件复制到新项目。上游文件不适用 Prism 的 MIT 许可。

更新时由维护者从官方来源取得新版本，检查许可，保留原字节和署名，更新 manifest 及已审核版权文件的导出哈希，再运行测试、严格编译并检查页面后随 Prism 发布。用户创建或编译项目时不自动检查或下载更新。官方示例图和 PDF 不进入仓库；生成的论文也不会随模板升级被改写。

模板字段、分层和新增模板步骤见[维护说明](template-registry.md)。
