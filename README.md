# github-learning-automation

把 **GitHub 仓库 → 可快速阅读、可长期刷新的 Obsidian 学习笔记**。

它不是 README 翻译器，也不是源码 Review 工具。当前版本优先回答：这个仓库是什么、能做什么、适合什么场景、官方资料明确写了怎样安装和使用、有哪些重要注意事项，并生成少量可检索标签。

## 设计思路

项目沿用 `bili-learning-automation` 已验证的原则：**确定性采集 → Agent 语义整理 → 质量门禁 → 原子发布**；笔记视觉语义兼容 `ComfyUI-Learning-Lab` 的 `learning-page` Core Design System。

```text
GitHub URL
  → 首次运行门禁：笔记路径 + GitHub 认证
  → prepare：仓库元数据 / README / 根目录 / 常见 manifest / Latest Release
  → source_bundle.md + analysis.json + agent_handoff.md
  → Agent 只基于来源填写 analysis.json
  → coverage review
  → finalize
  → 按 owner/repo 创建或 refresh Markdown
```

## 第一次使用

需要 Python 3.10+，核心代码没有第三方运行依赖。**不要求先安装全局 CLI**；在项目根目录直接使用项目 launcher：

```powershell
cd G:\GitHub\github-learning-automation
python scripts\github_learning.py doctor
```

第一次 `doctor` 会检查：

- 是否已经显式配置笔记目录；
- 当前是否检测到 GitHub 认证；
- 实际解析出的输出路径；
- `config/local.json` 是否存在。

如果没有配置，状态会是 `configuration_required`，`prepare` 会停止，不再静默写入项目内 fallback。

### 配置 Obsidian 输出目录

把 `--vault-root` 换成你自己的 Obsidian Vault 根目录（即直接包含 `.obsidian` 的那一层）：

```powershell
python scripts\github_learning.py configure `
  --vault-root "D:\Notes\MyVault" `
  --notes-subdir "GitHub-Note"
```

它会自动创建 `config/local.json`。示例仍保留在：

```text
config/local.json.example
```

最终笔记目录：

```text
<vault_root>\GitHub-Note
```

`config/local.json` 已被 `.gitignore` 排除。

### GitHub 登录与额度

程序按以下顺序寻找认证：

1. `GITHUB_TOKEN` / `GH_TOKEN`；
2. 已登录的 GitHub CLI：`gh auth token`；
3. 匿名模式。

Token 只在内存中使用，不写入项目、日志或笔记。

如果没有检测到登录，`doctor` 返回 `auth_recommended`；`prepare` 默认先停止并提示登录：

```powershell
gh auth login
```

如果明确愿意使用匿名 API，可以显式：

```powershell
python scripts\github_learning.py prepare "https://github.com/owner/repo" --allow-anonymous
```

匿名额度较低，不建议作为长期默认模式。

## 生成一篇笔记

先确认：

```powershell
python scripts\github_learning.py doctor
```

正常状态应为：

```json
{"status": "ready"}
```

然后：

```powershell
python scripts\github_learning.py prepare "https://github.com/ltdrdata/ComfyUI-Manager"
```

程序返回 `.runtime/github-learning/...` job 路径。Agent 阅读：

- `agent_handoff.md`
- `source_bundle.md`
- `analysis.json`

填写并复核 `analysis.json` 后：

```powershell
python scripts\github_learning.py finalize "<job_dir>"
```

正常发布返回：

```json
{
  "status": "note_ready",
  "publish_action": "created"
}
```

如果官方资料不足，正确结果是：

```json
{"status": "source_insufficient"}
```

这不是程序故障，也不会生成一篇看似完整但缺乏证据的笔记。

如果已经通过 `pip install -e .` 安装项目，`github-learning ...` 与项目 launcher 等价；Skill 不再假设这个全局命令一定存在。

## 同一仓库如何更新

`owner/repo` 是稳定身份。默认 `prepare` 使用 **upsert**：

- 第一次：创建笔记；
- 之后再次学习同一仓库：refresh 原笔记；
- 不再默认生成 `repo（2）.md`。

例如第二次 `finalize` 会返回：

```json
{
  "status": "note_ready",
  "publish_action": "refreshed"
}
```

新版笔记自动生成：

```markdown
## 我的记录
```

这个区域及其后的内容不会被 refresh 覆盖，适合保存你的实测、经验和补充。

如果确实希望同一仓库再生成一篇独立笔记：

```powershell
python scripts\github_learning.py prepare "https://github.com/owner/repo" --new-note
```

### 第一次测试留下的旧版笔记

v0.1 笔记没有 managed marker。为避免覆盖你可能已经人工修改的内容，第一次 refresh 会返回：

```text
legacy_note_refresh_blocked
```

确认允许迁移后再显式：

```powershell
python scripts\github_learning.py finalize "<job_dir>" --replace-legacy
```

程序会先把旧文件完整保存到当前 runtime job 的 `legacy_note_backup.md`，再刷新正式笔记。

## 同名仓库

不同 owner 可能存在相同 repo 名称。文件名默认保持简洁：

```text
demo.md
```

发生冲突时再加入 owner：

```text
demo · ownerB.md
```

真正的唯一身份始终是 Frontmatter：

```yaml
repo: "owner/repo"
```

## 笔记结构

章节按“有内容才出现”的原则生成，典型顺序：

```text
标题 / 仓库元信息
→ 先看结论
→ 它是什么
→ 能做什么
→ 适合什么场景
→ 如何使用（安装 / 基本使用 / 关键配置）
→ 官方资料冲突（存在时）
→ 注意事项
→ 仓库资料
→ 采集覆盖提醒（存在时）
→ 我的记录
```

标签总量最多 6 个，程序固定加入 `GitHub`，Agent 再提供 2-5 个高价值知识标签。

## 来源与可信度

当前只把以下资料作为事实依据：

- GitHub Repository metadata / Topics；
- README；
- 仓库根目录清单；
- 根目录中的常见安装/包管理 manifest；
- Latest Release（存在时）。

来源没明确写的版本、依赖、模型路径、兼容性、安装命令一律不补全。README 太少时应标记 `insufficient`，而不是生成看似完整的笔记。

如果官方来源之间明确冲突，例如 README 两处许可证说明不一致，Agent 会记录 `source_conflicts`，笔记只呈现冲突，不替维护者裁决。

manifest 和 Latest Release 属于可选补充来源。它们读取失败时不再让整个任务失败，而会记录为“采集覆盖提醒”；“没采到”不能写成“不存在”。

## API 请求优化

根目录清单已经包含 manifest 的 `download_url` 时，程序优先读取 GitHub Raw 内容，不再为每个 manifest 额外打一遍 Contents API。典型仓库因此主要消耗 Repository / README / Root Contents / Latest Release 等核心 API 请求。

## 时间

runtime 中 `collected_at` 保留 UTC 时间用于审计；笔记 Frontmatter 的 `updated` 使用运行机器的本地日期，避免 UTC 跨日导致 Obsidian 日期提前一天。

## ComfyUI 仓库

ComfyUI 插件不另走一套采集器。Agent 如果从官方来源确认它属于 ComfyUI，可用 `ComfyUI`、`插件`、`节点管理` 等标签，并优先提取：主要用途、节点/能力、安装方式、额外依赖、模型需求和使用入口；来源没有写就不补。

## 当前边界

当前暂不做：源码逐文件分析、Issues/Discussions 全量总结、PR Review、安全审计、自动比较多个仓库、自动生成 ComfyUI 工作流。

详见 `docs/ARCHITECTURE.md`、`docs/NOTE-SPEC.md`、`docs/QUICKSTART.md`。
