# 模板注册与兼容性

模板标识以投稿目标为中心：`generic/`、`family/`、`journal/`；出版社是说明信息。短名称是稳定的兼容别名，不随出版社变化。每个注册项选择可复用的构建配置，集中定义引擎、依赖、导入来源、示例和必要的构建隔离。

已有项目的 `prism-template.json` 保持只读兼容。新项目使用 `schema_version: 1`，同时记录短名称 `template`、规范名称 `template_id`、Prism 版本和引擎；两种名称必须指向同一模板。上游文件的版本或哈希单独记录，不写入本地来源路径。`--check-deps` 显式指定的 `--template` 继续优先于项目标识。

会议模板未来使用 `conference/<会议>/<年份>` 标识，并在注册项分别记录 `venue`、`edition`、`track` 和 `stage`。评审政策和模板的作者显示模式应分别描述；具体模式、年份和来源由对应会议模板实现与验证。未实现的会议不出现在可用模板列表中。

Nature 新项目记录 `variant: prism-article`（默认离线初稿）或 `sn-jnl`（显式本地官方导入）。旧 Nature 元数据缺少 `variant` 时按原 `sn-jnl` 模式处理，不改写文件；依赖检查按项目模式选择资源。其他模板不接受此字段。

默认初始化只复制仓库中的原创骨架和已审核的上游文件。上游文件集中在 `skills/paper-latex/assets/upstream/`，manifest 记录版本、来源、大小和 SHA-256，OUP 模板共享一份资源。`--template-source` 是本地高级覆盖入口，不触发网络请求。

新项目的 `language` 为 `bilingual`（默认）或 `english`。期刊混排使用 XeLaTeX 和独立中文字体样式，英文模式保留 pdfLaTeX；Prism 通用稿保留 XeLaTeX/LuaLaTeX。旧项目缺该字段时沿用原引擎和样式，不改写元数据或论文。`--check-deps --template NAME --language english` 可检查英文模式；对已有项目直接运行 `--check-deps` 按已记录模式检查。

同一期刊的内容骨架以文章类型区分，不增加期刊标识。NAR 声明 `research`（默认）、`database` 和 `web-server`，Angew 声明 `research`（默认）、`communication`、`review` 和 `minireview`。注册项的 `article_types` 驱动可选参数和初始化：共享目录先复制，再用所选稿型目录覆盖正文及对应补充材料；其余稿型不会进入项目。构建配置声明必要共享文件、排版资源与上游许可，不增加期刊专用复制分支。

`--article-type` 仅供支持多类型的模板初始化或依赖预览；普通构建不接受此选项。多类型项目在 schema 1 中记录 `article_type`，缺字段回退注册默认值；未知类型拒绝读取，不改写旧项目。此字段与 Nature 的来源 `variant` 分开。

`scripts/latex-templates.sh` 是默认按出版社分组的薄入口，复用 `--list-templates --group-by publisher`。分组与内容都来自同一注册表；通用模板单列，其余组按出版社名称排序，组内按期刊名和别名排序。仅多类型项目显示可传给 `--article-type` 的值；单类型显示用途。原 `--list-templates` 平铺输出保留，显式 `--group-by none` 与其一致；`--group-by` 仅允许列表查询，不读取研究项目或检查编译环境。
