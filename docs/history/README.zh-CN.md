# Git 历史迁移

[English](README.md) · [文档目录](../README.zh-CN.md)

2026-09-27，main 分支的提交元数据迁移到仓库维护者 Git 身份 `Sheng Wan <swan0624@uw.edu>`。这调整的是提交署名，不改变工作产生方式，也不表示项目全部由手工编写。

## 范围

- 从 26 次提交说明中移除 26 条 AI 共同作者 trailer；保留其余说明字节及所有 author/committer 日期。
- 原始 `939409aa0586bf9aa9b299c697cd5fa4b3dfd679` 发布了已授权的 RTX 3080 记录，其 author 和 committer 从 AI 身份改为 Sheng Wan。
- 其余 25 次原有 Sheng Wan author/committer 保持原样，未把真实第三方身份改为维护者。
- 只改写 `refs/heads/main`。事前核查没有标签、其他远端分支、PR 或签名提交；未移除既有签名，也未将改动后的失效签名描述为有效。

每对旧、新提交的 **Git 文件树完全相同**，父提交按映射连接。这 26 次历史提交中的代码、数据、许可、来源归属和原始验证产物未改变。README、当前署名规则、本说明及复现入口调整属于另一个新提交。

私有本地备份包含原始历史和完整工作目录，包括忽略文件；已完成归档读回、独立 bundle 克隆和 Git 对象核验。备份引用未上传公开远端。

## 编号映射

[commit-map.csv](commit-map.csv) 列出全部 26 对旧、新编号及共同文件树编号；[rewrite-audit.json](rewrite-audit.json) 保存逐提交身份、说明、日期和文件树检查。关键版本如下：

| 原始记录编号 | 内容相同的迁移编号 |
|---|---|
| `810591e6a77956a49dfef5de1d4a2274fefe9e07` | [`6476292d998185e6433e62dd2dff9a4c35afd837`](https://github.com/Tocqueville0624/amelia-torch/tree/6476292d998185e6433e62dd2dff9a4c35afd837) |
| `905cc79ce20e65fe5b673039d4e411db73cd7544` | [`a4c74cd9ce141d1291437ba602f5f330442d9241`](https://github.com/Tocqueville0624/amelia-torch/tree/a4c74cd9ce141d1291437ba602f5f330442d9241) |
| `ef729c093e162f4d6ebd797c95a9da8072ac968a` | [`90699b898a55a9c29f61e01181b8d688ab08b702`](https://github.com/Tocqueville0624/amelia-torch/tree/90699b898a55a9c29f61e01181b8d688ab08b702) |
| `06b0fe8587aca7b781281974f6377433e30ceb05` | [`80ee4ca4a9d79d94bfb8371c1a4c2f53cf074d0a`](https://github.com/Tocqueville0624/amelia-torch/tree/80ee4ca4a9d79d94bfb8371c1a4c2f53cf074d0a) |
| `939409aa0586bf9aa9b299c697cd5fa4b3dfd679` | [`fa556bafe64fbf90a010ff04347e60c5d5da3b5f`](https://github.com/Tocqueville0624/amelia-torch/tree/fa556bafe64fbf90a010ff04347e60c5d5da3b5f) |
| `ee973a63a3124ce730ec5c0fb4be8b3abb816060` | [`8a2d5c131ce7ff5748a1cebe31ecb37006137039`](https://github.com/Tocqueville0624/amelia-torch/tree/8a2d5c131ce7ff5748a1cebe31ecb37006137039) |


原始测量报告保留当时的提交编号和源码校验值。新编号表示内容相同的迁移提交，不冒充实验当时记录的版本。已有 CI 仍是原始源码版本的证据，不是迁移后的新执行。原始报告与归档源码快照不改写。

在新克隆中查找旧版本对应编号，再检出：

```powershell
$revision = Import-Csv .\docs\history\commit-map.csv |
    Where-Object { $_.old_commit -like '810591e*' }
if (@($revision).Count -ne 1) { throw 'Expected one revision match' }
git switch --detach $revision.new_commit
```

历史检出只包含当时已有文件，不一定含后加的迁移文档；映射始终可在 main 查看。CSV 中共同文件树编号用于独立确认内容一致。

## 复现入口与 CI

Colab 模板现在固定检出原始 `ef729c0` 对应的新编号。仅调整检出常量、说明和链接，其余可执行单元内容不变。[reference-updates.json](reference-updates.json) 记录这处调整及三个固定源码链接。当前云端文档同时说明两个编号。模板没有重新执行，原有限制仍适用。

已检查工作流定义和 action 引用：它们未固定指向被改写的项目提交，因此保持原样。发布提交使用 `[skip ci]`。本次没有启动拟合、模拟、性能实验或测试套件。既有 CI 与基准输出保留原始编号。

静态复核还修正了此前六份文档校验清单中的 12 个 README 条目：相对文件名曾误解析到仓库根目录。新值按各清单实际目录计算；非 Markdown 产物的条目未改变。上次文档审查清单作为历史记录保留，修正前后哈希见 [editorial-audit.json](editorial-audit.json)。

## Windows 重新同步

建议克隆到新目录，保留旧目录直到本地工作已转移并核对。先在旧仓库查看状态：

```powershell
git status --short
git branch --show-current
Set-Location ..
git clone https://github.com/Tocqueville0624/amelia-torch.git amelia-torch-clean
Set-Location amelia-torch-clean
git config --local user.name "Sheng Wan"
git config --local user.email "swan0624@uw.edu"
git fetch origin
git rev-parse HEAD origin/main
```

若 amelia-torch-clean 已存在，换用未占用的目录名；最后两个编号应一致。只转移仍需要的本地文件，检查差异后提交到新历史。实验结果单独保留；不复制旧 .git、不合并旧 main。在旧检出中执行 pull 或 merge 可能重新接回旧历史，应避免。旧虚拟环境可能包含绝对路径，恢复运行工作时再单独配置新环境。

不要从旧克隆或备份执行 `git push --all` 或 `git push --mirror`。如有未发布提交，应逐个检查补丁，将需要的改动应用到新历史，避免带回已移除的 trailer 或改变第三方归属。

## 仍可能保留的痕迹

分支历史改写不会清空 GitHub 缓存、旧提交 URL、Actions 记录、fork、本地 reflog 或其他克隆。编号映射与原始报告有意保留旧编号，以便追溯。其他位置未来产生的 PR 引用也不属于本次分支更新范围。不能保证所有历史副本或平台缓存均已移除。
