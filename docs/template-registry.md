# 模板注册与兼容性

模板标识以投稿目标为中心：`generic/`、`family/`、`journal/`；出版社是说明信息。短名称是稳定的兼容别名，不随出版社变化。每个注册项选择可复用的构建配置，集中定义引擎、依赖、导入来源、示例和必要的构建隔离。

已有项目的 `prism-template.json` 保持只读兼容。新项目使用 `schema_version: 1`，同时记录短名称 `template`、规范名称 `template_id`、Prism 版本和引擎；两种名称必须指向同一模板。上游文件的版本或哈希单独记录，不写入本地来源路径。`--check-deps` 显式指定的 `--template` 继续优先于项目标识。

会议模板未来使用 `conference/<会议>/<年份>` 标识，并在注册项分别记录 `venue`、`edition`、`track` 和 `stage`。评审政策和模板的作者显示模式应分别描述；具体模式、年份和来源由对应会议模板实现与验证。未实现的会议不出现在可用模板列表中。

Nature 新项目记录 `variant: prism-article`（默认离线初稿）或 `sn-jnl`（显式本地官方导入）。旧 Nature 元数据缺少 `variant` 时按原 `sn-jnl` 模式处理，不改写文件；依赖检查按项目模式选择资源。其他模板不接受此字段。

默认初始化只复制仓库中的原创骨架和已审核的上游文件。上游文件集中在 `skills/paper-latex/assets/upstream/`，manifest 记录版本、来源、大小和 SHA-256，OUP 模板共享一份资源。`--template-source` 是本地高级覆盖入口，不触发网络请求。

新项目的 `language` 为 `bilingual`（默认）或 `english`。期刊混排使用 XeLaTeX 和独立中文字体样式，英文模式保留 pdfLaTeX；Prism 通用稿保留 XeLaTeX/LuaLaTeX。旧项目缺该字段时沿用原引擎和样式，不改写元数据或论文。`--check-deps --template NAME --language english` 可检查英文模式；对已有项目直接运行 `--check-deps` 按已记录模式检查。

同一期刊的内容骨架以文章类型区分，不增加期刊标识。NAR 声明 `research`（默认）、`database` 和 `web-server`，Angew 声明 `research`（默认）、`communication`、`review` 和 `minireview`，Advanced Science 声明 `research`（默认）、`review` 和 `perspective`。注册项的 `article_types` 驱动可选参数和初始化：共享目录先复制，再用所选稿型目录覆盖正文及对应补充材料；其余稿型不会进入项目。构建配置声明必要共享文件、排版资源与上游许可，不增加期刊专用复制分支。

Advanced Science 使用独立的轻量 `article` 构建配置，共用 `prism-wiley-numeric.bst`。它不加载 Angew 的历史 Wiley class，也不改变 Angew 的既有样式；所需资源通过注册表声明，初始化时验证后复制。

`--article-type` 仅供支持多类型的模板初始化或依赖预览；普通构建不接受此选项。多类型项目在 schema 1 中记录 `article_type`，缺字段回退注册默认值；未知类型拒绝读取，不改写旧项目。此字段与 Nature 的来源 `variant` 分开。

## 查询与校验

`scripts/latex-templates.sh` 是默认按出版社分组的薄入口。分组与内容都来自同一注册表；通用模板单列，其余组按出版社名称排序，组内按期刊名和别名排序。仅多类型项目显示可传给 `--article-type` 的值；单类型显示用途。原 `scripts/latex-paper.sh --list-templates` 平铺输出保留，显式 `--group-by none` 与其一致。查询不读取当前论文，也不要求网络或 TeX。

```bash
scripts/latex-templates.sh --show advanced-science
scripts/latex-templates.sh --show advanced-science --json
scripts/latex-templates.sh --validate
python3 scripts/sync-template-docs.py --check
```

详情 JSON 带独立接口版本，路径相对仓库。它描述模板标识、出版社、稿型、语言与引擎策略、初始化文档角色、来源、说明路径，以及稿型选择和本地官方包导入能力。文档角色描述新项目的起点，不替代已有项目的实际构建入口。

离线 `--validate` 检查显式定义、全部稿型资源、路径边界、共享样式、上游许可及哈希和说明链接，不修改文件。它不认证字数、提案资格、期刊当前政策或最终投稿合规性。

## 新增或维护模板

1. 在共享实现的显式、不可变目录中声明身份、构建配置、语言策略、资源、来源和文档角色。短别名保持稳定，不通过扫描目录自动注册，也不新增外部配置依赖。
2. 在 `skills/paper-latex/assets/` 维护原创骨架与已核实许可的资源；共享构建配置复用依赖和隔离策略。第三方文件保留原字节、许可、来源及哈希。为新模板添加 `docs/templates/<短名称>.md`，把来源、草稿适用范围和人工投稿提示放在该页。
3. 运行初始化、全部稿型与语言契约测试，并严格编译合成正文、补充材料和示例，检查正常阅读尺度下的首页、密集图表、引用和代表分页。特殊引用规则和上游兼容性另作针对性验证。
4. 运行 `python3 scripts/sync-template-docs.py --write`，仅更新 README、简明指南和模板目录中的标记块；再用 `--check` 检测漂移。手写投稿说明不由此工具生成。校验或同步文档都不会自动扩充公开文件清单。
5. 逐项审核新增文件和所有公开差异，再手动维护 `scripts/public-export-files.txt`、版本和 CHANGELOG，执行公开导出隐私检查。研究稿件、保护文件、私有报告及验证输出留在清单之外。

工作流实现集中在 `scripts/lib/prism_latex/`；skill 内 Python 文件仅保留兼容入口。目录定义、项目解析与初始化、编译执行、结果发布分别维护；三个工作流各自处理输入语义。修改公共层时回归笔记日期与完整 TeX、审稿保密分离及双份发布、论文多文件和旧元数据兼容。

## 实现边界

以下路径均相对于 `scripts/lib/prism_latex/`：

| 模块 | 维护职责 |
| --- | --- |
| `catalog_models.py`、`catalog.py` | 不可变数据模型、显式模板定义、可复用构建配置与查询 |
| `catalog_validation.py` | 离线检查全部声明、资源、许可哈希与说明链接 |
| `project.py` | 一次读取项目记录，统一旧字段默认值，不改写项目 |
| `template_assets.py`、`initialization.py` | 校验来源，生成明确文件计划，暂存与安全替换 |
| `runtime.py` | 管理工作目录，执行 `BuildJob` 并返回 `BuildResult`；通过明确的 `Artifact` 列表发布，失败时回滚 |
| `notes.py`、`reviewer.py`、`paper.py` | 分别处理笔记、审稿和论文语义，选择任务与交付路径 |
| `build_support.py`、`build_script.py` | 字体、依赖、严格检查及可移植重建脚本 |
| `templates.py` | 原有模板 API 的兼容接口 |

编译任务不选择交付目录，也不发布文件。审稿适配器先完成作者稿和编辑稿全部编译，再发布明确的两份文件；不扫描或复制整个临时目录。多个输出在普通文件操作失败时回滚，不能视作断电时跨文件的原子事务。不同工作流的输入解析器保持独立。
