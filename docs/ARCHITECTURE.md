# 架构说明

## 主链路

```text
GitHub URL / owner/repo
→ doctor / first-run gate
→ config：显式确定笔记输出目录
→ auth：环境 Token → GitHub CLI → 显式匿名
→ input_resolver 规范化 owner/repo
→ github_client 只读采集官方 GitHub 资料
→ lifecycle.prepare 写 runtime job
→ Agent 根据 source_bundle 建立语义分析
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

旧版笔记没有 marker 时，`--replace-legacy` 是显式迁移开关；启用前程序会在 runtime job 写入 `legacy_note_backup.md`，不静默丢失原文。

## GitHub 采集与 API 降级

核心来源：Repository metadata、README、根目录。核心来源失败会停止任务。

可选来源：根目录 manifest、Latest Release。它们失败时不再杀掉整个 `prepare`，而是进入 `collection_warnings`。

根目录 API 返回的 `download_url` 会优先用于读取 manifest，从而避免对每个 manifest 再做一次 Contents API 调用；只有没有 Raw 地址时才回退到 Contents API。

## 时间语义

`collected_at` 保留 UTC ISO 时间用于审计；`collected_local_date` 使用运行机器的本地时区。笔记 Frontmatter 的 `updated` 使用本地日期，避免 UTC 跨日导致 Obsidian 日期显示提前一天。

## 来源冲突与采集缺口

二者必须分开：

- `source_conflicts`：官方来源本身互相矛盾，由 Agent 判断并在正文显示 `[!risk]`；
- `collection_warnings`：采集器没有拿到某个可选来源，由程序记录并在正文显示 `[!meta]`。

“没采到”不能写成“不存在”。

## 状态而不是异常

以下属于预期业务状态，不应伪装成程序错误：

- `configuration_required`
- `auth_recommended`
- `analysis_required`
- `source_insufficient`
- `legacy_note_refresh_blocked`
- `duplicate_repository_notes`
- `note_ready`

只有无效配置、无效 runtime 路径、未知分析状态、核心网络/解析故障等才属于真正 error。

## 确定性边界

程序负责：URL、仓库元数据、来源包、Frontmatter、H1、标签上限、章节渲染、输出路径、repo identity、refresh、文件名冲突策略、runtime 安全边界、首次运行门禁和认证方式选择。

Agent 负责：判断来源是否充分；提炼“是什么 / 能做什么 / 场景 / 安装 / 使用 / 配置 / 注意事项”；识别官方来源冲突；生成 2-5 个知识标签；覆盖复核。
