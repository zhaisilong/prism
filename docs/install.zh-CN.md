# 安装 LaTeX 与 Prism

选择对应系统安装 TeX Live。完整发行版包含中英混排和常用期刊宏包，下载及安装需要数 GB 空间。Prism 还需要 Python 3.9+、Git 和 `latexmk`。

## macOS

1. 从 [MacTeX 官方下载页](https://www.tug.org/mactex/mactex-download.html)下载并安装完整 MacTeX。
2. 安装后重新打开终端，检查：

   ```bash
   python3 --version
   xelatex --version
   latexmk --version
   ```

MacTeX 会配置 `/Library/TeX/texbin`。如果终端找不到命令，先重新打开终端；仍有问题时可在当前终端运行 `export PATH="/Library/TeX/texbin:$PATH"`。BasicTeX 是精简发行版，可能需要另行补装中文字体和期刊宏包；首次使用建议完整 MacTeX。

## Linux

选择与你的发行版对应的命令。安装需要管理员权限，并会下载完整 TeX Live。

**Ubuntu / Debian：**

```bash
sudo apt update
sudo apt install python3 git texlive-full latexmk
```

**Fedora：**

```bash
sudo dnf install python3 git texlive-scheme-full latexmk
```

**Arch Linux：**

```bash
sudo pacman -S python git texlive-meta texlive-langchinese
```

Arch 的 `texlive-meta` 包含 `latexmk`，中文支持需要另外安装 `texlive-langchinese`。其他 Linux 可参照 [TeX Live 官方安装说明](https://tug.org/texlive/)安装完整发行版，并把安装程序提示的 `bin` 目录加入 `PATH`。发行版的软件源可能提供较旧的 TeX Live；若依赖检查仍缺少宏包或编译器功能，请使用较新的发行版或官方 TeX Live。

## 安装 Prism 并检查

```bash
git clone https://github.com/zhaisilong/prism.git
cd prism
python3 scripts/install-paper-skill.py
scripts/latex-paper.sh --check-deps --template nature
```

最后一条命令显示缺失项。新论文默认用 XeLaTeX 支持中英混排，模板本身无需联网下载。完整 TeX 安装不包含官方 Nature `sn-jnl` 模板包；只有选择其官方变体时才需按[高级用法](reference.zh-CN.md)提供本地 ZIP。

准备好后，按[三步指南](guide.zh-CN.md)创建并编译论文。缺少编译器、中文字体或期刊宏包时，使用 `--check-deps` 查看具体名称，并通过当前 TeX 发行版的包管理方式补齐；不要混用系统包管理器和另一套 TeX Live 的 `tlmgr`。若编译失败，保留日志交给 Codex 检查即可。

安装命令和软件包名称参考 [Debian](https://packages.debian.org/stable/texlive-full)、[Fedora](https://packages.fedoraproject.org/pkgs/texlive/texlive-scheme-full/) 和 [Arch Linux](https://archlinux.org/packages/extra/any/texlive-meta/) 官方包信息。
