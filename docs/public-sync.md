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

输出目录与 manifest 文件都必须尚不存在，父目录需已存在。白名单包含根目录通用文档、许可、Git 文本配置、`VERSION`、`projects/.gitkeep` 和 `scripts/`、`skills/`、`tests/`、`docs/` 内的维护文件。导出校验常规文件、大小、权限和 SHA-256；复制中源文件变化会中止。

研究文件、archives、根目录 `.bib`、旧模板目录、机器配置、缓存和构建产物不导出。符号链接、嵌套 Git 元数据、意外二进制和敏感文本会阻止导出。扫描报告给出文件与规则，不回显凭证内容。扫描只能辅助检查，推送前仍需审阅文件清单和 diff。

维护的 demo `.tex/.bib` 与许可允许分发的 OUP、Science 上游样式可以公开，保留来源、原始版权和许可。Nature `sn-jnl` 官方包仍只通过显式本地导入使用。模板内的演示 bibliography 可以公开；个人根 bibliography 不可公开。

上游版权中的必要邮箱只对代码内已审核的精确路径和 SHA-256 放行；改动字节、复制到其他路径或添加个人邮箱都会拒绝。凭证和个人路径扫描没有此例外。安装 skill 产生的本机路径、安装备份及研究内容不进入导出。

## 首次同步

只在已审核的独立导出目录内初始化 Git，复核远程为空，再提交代码快照。设置该仓库专属的 GitHub noreply 身份，不修改全局 Git 配置。原仓库不添加指向公开远程的推送配置。

代码版本以 `VERSION` 为准，标签使用 `vYYYY.MM.DD` 或同日后缀。推送仅包含独立代码历史的 `main` 与所需日期标签；不推送原仓库历史，不使用强推。

## 后续同步

继续使用同一独立代码 checkout，先拉取并检查远程状态，再从新的已审核快照更新文件、查看 diff、运行测试并创建提交。保留该 checkout 的 `.git`；不要把原仓库的 `.git` 复制过去，也不要把整个研究目录作为同步源。

若远程出现预期外提交或拒绝推送，先调查差异。版本和标签日期按 `Asia/Shanghai`，运行工具不会自动升版或自动推送。导出清单放在被忽略的 archives 中，便于本地复核。
