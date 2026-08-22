# GitHub 项目转笔记

本项目把 GitHub 仓库官方资料整理成简洁、可检索、可长期维护的 Markdown 学习笔记。

## 入口

不要假设全局 `github-learning` 已安装。默认从项目根目录使用：

```powershell
python scripts\github_learning.py <command>
```

如果 `github-learning` 已安装，可作为等价入口。

## 首次运行门禁

每次开始真实采集前先执行 `doctor`，首次运行尤其不能跳过：

```powershell
python scripts\github_learning.py doctor
```

- `configuration_required`：先询问用户笔记保存位置，再使用 `configure` 写入 `config/local.json`；禁止静默使用项目 fallback。
- `auth_recommended`：说明尚未检测到 GitHub 登录。优先让用户执行 `gh auth login`；只有用户明确接受匿名额度时才使用 `--allow-anonymous`。
- `ready`：可以继续采集。

程序自动优先复用 `GITHUB_TOKEN` / `GH_TOKEN` 或本机已登录的 `gh auth token`，不得把 Token 写入仓库、配置文件、日志、笔记或回复。

笔记位置必须由使用者在本机显式配置，不要把任何具体 Vault 路径当成默认值写进代码或文档。未配置时按下面的形式引导用户：

```powershell
python scripts\github_learning.py configure --vault-root "D:\Notes\MyVault" --notes-subdir "GitHub-Note"
```

## 正式流程

1. `doctor` 必须允许继续。
2. 默认运行 `prepare <GitHub URL>`；这会使用 `upsert`，同一 `owner/repo` 后续自动 refresh。
3. 只有用户明确要保留第二份独立笔记时才使用 `prepare --new-note`。
4. 读取返回 job 目录中的 `agent_handoff.md`、`source_bundle.md` 和 `analysis.json`。
5. 只根据 `source_bundle.md` 填写 `analysis.json`；不得使用模型记忆补版本、安装命令、路径、兼容性或功能。
6. 来源不足时把 `source_status` 设为 `insufficient`；这是正常完成状态，不是异常。
7. 如果官方来源彼此明确矛盾，写入 `source_conflicts`；只记录冲突，不自行裁决。
8. `Collection warnings` 表示可选来源没有采到，不代表仓库没有该内容；不得把采集失败改写成“没有 Release / 没有配置”。
9. 来源充分时完成覆盖复核，把 `coverage_review.status` 设为 `passed`。
10. 运行 `finalize <job_dir>`；只有 `note_ready` 才能声称笔记已经发布。

## Refresh 安全边界

v0.2+ 笔记的 managed marker 之后是用户保留区，默认从 `## 我的记录` 开始。Agent 不要把自动生成内容写到个人区，也不要在 refresh 时删除或重写个人区。

旧版无 marker 笔记返回 `legacy_note_refresh_blocked` 时，不得自动追加 `--replace-legacy`。先说明风险；只有用户明确允许迁移时才能执行。程序会先把原文件保存为 runtime `legacy_note_backup.md`。

如果同一 `owner/repo` 找到多篇笔记而返回 `duplicate_repository_notes`，停止自动刷新并让用户先确认，不要猜哪篇是主笔记。

笔记核心只回答：这个仓库是什么、能干嘛、适合什么场景、如何安装/使用、需要注意什么。不要把 README 目录机械改写成笔记，也不要做无请求的源码审计。
