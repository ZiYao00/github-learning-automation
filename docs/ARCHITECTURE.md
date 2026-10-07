# 架构说明

## 主链路

```text
GitHub URL / owner/repo
→ doctor / first-run gate
→ config：显式确定笔记输出目录
→ auth：环境 Token → GitHub CLI → 显式匿名
→ input_resolver 规范化 owner/repo
→ github_client 固定 HEAD revision，只读采集官方 GitHub 资料
→ source_planner 在预算内选择高价值补充文档
→ lifecycle.prepare 写 source_manifest / sources / runtime job
→ Agent 根据当前 Job 来源建立语义分析
→ coverage review
→ lifecycle.finalize 按 repo identity 创建或 refresh
→ Markdown
```

## 首次运行门禁

首次运行不是文档提示，而是程序状态机：

- `configuration_required`：没有显式笔记目录；`prepare` / `finalize` 都不得写入项目 fallback。
- `auth_recommended`：没有检测到 GitHub 认证；默认不开始匿名采集。
- `ready`：输出目录和认证都已准备好。

匿名模式仍被支持，但必须通过 `--allow-anonymous` 显式选择。

## CLI / Launcher

项目保留 setuptools console script：`github-learning`。同时提供零安装项目 launcher：

```text
scripts/github_learning.py
```

Skill 默认调用 launcher，因此不会因为用户没有执行 `pip install -e .` 而出现 command not found。

## GitHub 认证边界

认证解析顺序：

1. `GITHUB_TOKEN` / `GH_TOKEN`；
2. 本机 `gh auth token`；
3. anonymous。

Token 只进入请求 Header，不进入 runtime、配置、日志或 Markdown。

## Repository identity 与发布策略

稳定身份是 `owner/repo`，而不是文件名。

`prepare` 默认写入 `publish_mode=upsert`：

- 没有该 repo 的笔记 → 创建；
- 已有且是 v0.2+ managed note → 原路径 refresh；
- 同一 repo 找到多篇 → `duplicate_repository_notes`，停止自动刷新；
- 已有旧版无 marker 笔记 → `legacy_note_refresh_blocked`，默认不覆盖。

只有显式 `--new-note` 才使用 `publish_mode=new` 创建另一份独立笔记。

同名不同 owner 时，文件名冲突项使用 `repo · owner.md`，但 Frontmatter 的 `repo` 仍是唯一身份。

## Managed region

自动生成正文位于：

```text
GITHUB_NOTE_MANAGED_START
...
GITHUB_NOTE_MANAGED_END
```

refresh 会重建 Frontmatter 和 managed region，并原样保留 `MANAGED_END` 之后的个人区域。这样仓库更新和用户实测可以共存在一篇笔记中。

旧版笔记没有 marker 时，`--replace-legacy` 是显式迁移开关。新 job 会记录授权目标路径与 SHA-256；如果目标在 prepare→finalize 之间变化，返回 `legacy_target_changed` 并要求重新授权。目标未变化时，程序会在覆盖前写入 runtime `legacy_note_backup.md`，不静默丢失原文。

## GitHub 采集、Snapshot 与 Source Planner

prepare 首先解析默认分支 HEAD commit，并把本轮仓库文件采集固定到该 revision，避免 README、manifest 与 docs 混入不同提交状态。

核心来源：Repository metadata、HEAD commit、README、根目录。核心来源失败会停止任务。

Source Planner 基于 Git tree 做有限深度选择，并把 README 中明确链接的官方文档作为强信号。它优先读取根 manifest、顶层/有效 Skill 与 Agent metadata，以及 quickstart / support matrix / install / usage / architecture / validation / compatibility 等高价值文档；同时过滤 vendor、node_modules、build/dist 等噪音目录，避免把深层第三方 AGENTS.md 或大量 Compose/config 文件误当成项目学习主资料。它受文件数量、单文件大小和总预算限制，不是全仓库抓取器。

Latest Release 属于当前发布状态补充来源，不参与 commit snapshot；可选来源失败会进入 `collection_warnings`，不等于仓库不存在对应内容。

`source_manifest.json` 记录 revision、来源路径、类型、SHA、原始/保存大小、截断状态与本地 runtime 文件，是来源审计真源；`source_bundle.md` 只是 Agent 便利视图。

## 时间语义

`collected_at` 保留 UTC ISO 时间用于审计；`collected_local_date` 使用运行机器的本地时区。笔记 Frontmatter 的 `updated` 使用本地日期，避免 UTC 跨日导致 Obsidian 日期显示提前一天。

## 来源冲突与采集缺口

二者必须分开：

- `source_conflicts`：官方来源本身互相矛盾，由 Agent 判断并在正文显示 `[!risk]`；
- `collection_warnings`：采集器没有拿到某个可选来源，由程序记录并在正文显示 `[!meta]`。

“没采到”不能写成“不存在”。

## Shared Obsidian style dependency

本项目只消费共享样式，不拥有 CSS 真源。Provider 是：

```text
https://github.com/ZiYao00/obsidian-learning-snippets
```

`config/obsidian-style.json` 是机器可读的 Consumer Contract，声明 Core、Extension 与 `cssclasses`。项目模板负责持续输出 `learning-page` + `github-note`；共享 CSS 的内容和版本在 Provider 仓库维护。本项目不通过受 Git 跟踪的 `obsidian/snippets/` junction 分发 CSS。

## Runtime 恢复与幂等

v0.3 Job 写入 `state`。同一 `owner/repo` 存在 `analysis_required` / `analysis_complete` 等未完成状态时，默认 prepare 返回 `in_progress`，让 Agent 继续已有 Job；不会重复访问 GitHub。只有显式 `--restart-job` 才重新采集，并把旧活动 Job 标记为 `superseded`，不删除审计资料。

成功发布后 Job 进入 `published` 并保存 final result。再次 finalize 会直接返回同一发布结果并标记 `idempotent=true`。

## 不可信来源与私有仓库边界

仓库正文只作为数据证据。README、SKILL.md、AGENTS.md、docs、Release 中的 Agent/系统指令或命令要求不能改变当前任务，也不能触发代码执行或文件操作。私有仓库即使凭据可读也默认返回 `private_repository_blocked`。

## 状态而不是异常

以下属于预期业务状态，不应伪装成程序错误：

- `configuration_required`
- `auth_recommended`
- `analysis_required`
- `in_progress`
- `source_insufficient`
- `private_repository_blocked`
- `legacy_note_refresh_blocked`
- `legacy_target_changed`
- `duplicate_repository_notes`
- `note_ready`

只有无效配置、无效 runtime 路径、未知分析状态、核心网络/解析故障等才属于真正 error。

## 确定性边界

程序负责：URL、仓库元数据、来源包、Frontmatter、H1、标签上限、章节渲染、输出路径、repo identity、refresh、文件名冲突策略、runtime 安全边界、首次运行门禁和认证方式选择。

Agent 负责：判断来源是否充分；提炼“是什么 / 能做什么 / 场景 / 安装 / 使用 / 配置 / 注意事项”；识别官方来源冲突；生成 2-5 个知识标签；覆盖复核。
