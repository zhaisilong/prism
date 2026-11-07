# 公开代码同步

公开目标为 [zhaisilong/prism](https://github.com/zhaisilong/prism)。研究数据留在本地。原仓库历史曾包含后来排除的资料和旧模板；`.gitignore` 不会从历史中删除文件，因此首次同步使用独立的全新代码历史。

## 审核与导出

```bash
python3 -B scripts/export-public-code.py --check
mkdir -p archives/2026-10-24
python3 -B scripts/export-public-code.py \
  --out archives/2026-10-24/public-code \
  --manifest archives/2026-10-24/public-export-manifest.json
```

输出目录与 manifest 文件都必须尚不存在，父目录需已存在。`scripts/public-export-files.txt` 逐项列出允许公开的文件，包括清单自身。新增维护文件须显式加入清单并审核；维护目录内有未列文件或清单文件缺失时，导出失败。清单只接受精确相对文件路径，不接受目录、通配符、重复项或越界路径。缓存等已有排除项继续忽略。

导出校验常规文件、大小、权限和 SHA-256；复制中源文件变化会中止。只有 `projects/.gitkeep` 可以进入公开项目目录，其余研究目录不会被遍历。

发布涉及本地研究案例时，可重复使用 `--protect-file` 指定私有正文、文献、报告或数据文件；检查和导出均支持该参数：

```bash
python3 -B scripts/export-public-code.py --check \
  --protect-file PRIVATE_MAIN.tex \
  --protect-file PRIVATE_REFERENCES.bib
```

工具仅在内存中比较整文件 SHA-256，可拦截改名后的完整复制；不将私有文件路径、内容或哈希写入导出清单。保护文件必须为不经符号链接的常规文件，检查期间变化即中止。整文件哈希不能识别局部摘录、改写或重排，因此所有公开示例必须使用合成内容，并审核已允许文件的修改差异。私有预览、报告和保护文件参数记录均保留在临时目录或被忽略的 archives 中。

研究文件、archives、根目录 `.bib`、旧模板目录、机器配置、缓存和构建产物不导出。符号链接、嵌套 Git 元数据、意外二进制和敏感文本会阻止导出。扫描报告给出文件与规则，不回显凭证内容。扫描只能辅助检查，推送前仍需审阅文件清单和 diff。

维护的 demo `.tex/.bib` 与许可允许分发的 OUP、Science、Wiley 上游样式可以公开，保留来源、原始版权和许可。Nature `sn-jnl` 官方包仍只通过显式本地导入使用。模板内的演示 bibliography 可以公开；个人根 bibliography 不可公开。

上游版权中的必要邮箱只对代码内已审核的精确路径和 SHA-256 放行；改动字节、复制到其他路径或添加个人邮箱都会拒绝。凭证和个人路径扫描没有此例外。安装 skill 产生的本机路径、安装备份及研究内容不进入导出。

## 首次同步

只在已审核的独立导出目录内初始化 Git，复核远程为空，再提交代码快照。设置该仓库专属的 GitHub noreply 身份，不修改全局 Git 配置。原仓库不添加指向公开远程的推送配置。

代码版本以 `VERSION` 为准，标签使用 `vYYYY.MM.DD` 或同日后缀。推送仅包含独立代码历史的 `main` 与所需日期标签；不推送原仓库历史，不使用强推。

## 后续同步

继续使用同一独立代码 checkout，先拉取并检查远程状态，再从新的已审核快照更新文件、查看 diff、运行测试并创建提交。保留该 checkout 的 `.git`；不要把原仓库的 `.git` 复制过去，也不要把整个研究目录作为同步源。

若远程出现预期外提交、标签冲突、敏感匹配或拒绝推送，先调查差异。版本和标签日期按 `Asia/Shanghai`，运行工具不会自动升版或自动推送。导出清单放在被忽略的 archives 中，便于本地复核。发布时核对暂存文件与快照哈希，仅推送审核后的 `main` 和日期标签；GitHub Release 只放通用更新说明，不附研究文件或本地验证报告。
