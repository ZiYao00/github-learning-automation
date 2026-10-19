# github-learning-automation

把公开 **GitHub 仓库 → 可长期复用的个人知识资产**。

v0.4.1 的主题仍是 **Durable Knowledge Capture**，这次重点把首次配置与本地目录拓扑收完整。它不是 README 翻译器、源码 Review 工具或完整 GitHub Research Agent，而是把一次收藏拆成三个职责明确的 Artifact：

- **Research Packet**：长期、不可变、可复核的事实底座；
- **Capture Note**：写入 Obsidian、优先给人快速阅读的收藏入口；
- **Derived Artifact**：以后按需生成的 Deep Note / Compare / Media Brief。

## 设计思路

核心原则是 **Capture First，Derive Later**：先可靠保存仓库证据，再生成轻量 Capture Note；以后深度学习、项目对比或制作项目介绍时重新消费同一份 Research Packet。

```text
GitHub URL
  → 首次运行门禁：笔记路径 + Research Root + GitHub 认证
  → prepare：固定 HEAD revision + Source Planner
  → runtime Job v8（历史 v6/v7 兼容）
  → Research Packet staging / hash validate / immutable archive
  → Agent：why_save + adaptive map + Evidence Map + coverage review
  → finalize
  → Full Capture Note 或 Minimal Capture Note
```

Research Packet 在 Agent 分析前完成。因此“资料不足”不再等于“收藏失败”。

### V2.2 默认阅读体验（Unreleased）

新的 `sufficient` Job 默认按 **A 版自然产品解读** 生成 Capture Note：Agent 在 `analysis.json` 中填写 `editorial_headline` / `editorial_body`，用简洁、具体、来源可复核的文字解释项目的实际价值与独特能力，而非拼接重复的功能清单。底层 `summary`、`why_save`、`knowledge_map`、`evidence_map` 等字段保留用于检索、追溯与质量验证。资料不足时仍生成 Minimal Note；旧 Job 保持原渲染。

**官方亮点摘要：** 如果 README 明确列出有价值的官方 Features/Highlights/核心模块，新文章先简要归纳这些能力，再用实际场景解释最重要的部分；不强求固定数量。隐私、云端、遥测类说法必须标注为仓库自述，并保留作者披露的联网例外和可选 API 条件。

**目录约定：** 阅读层使用 `00-待整理` 作为待整理文件夹名；`_repo-data` 保持文件存在，但通过共享 `github-note.css` 在 Obsidian 文件树隐藏。已有正式笔记不自动移动。

**编辑式阅读 CSS：** 共享 `obsidian-learning-snippets` 的 `github-note.css` v0.4 只优化 GitHub 笔记的标题层级、段落节奏、官方功能列表与源码/引用显示；保留 Obsidian 主题、阅读宽度设置及普通 Markdown 编辑。质量门禁、Golden Sample 和跨类型验收见 `docs/NOTE-SPEC.md`。

**跨 Agent 统一契约：** 新任务为 Job v8、写作契约 2.2、Skill 2.4.0；任何 Agent 都须通过统一 `prepare → analysis.json → finalize` 流程。正式发布前强制检查新版正文及 `editorial_review`，旧 v6 Job 仍兼容。`Skill` 同步包附带黄金样板、NOTE-SPEC 和契约清单，并生成可重新导入网页版 ChatGPT 的 `release/skill.zip`。新笔记放入 `00-待整理`，旧笔记原位刷新。该机制约束统一入口，不能阻止绕过程序直接写文件的外部工具。

**原文与 Prompt 组件（按需）：** README 等来源有必要的官方逐字短引文时使用 `> [!gh-source]`（附 pinned 来源链接、清楚标注译文）；确实取得且核查完整的作者原始 Prompt 时使用 `~~~prompt`（保留原文、原生按钮复制、320px 内滚动）。只是资源路径或普通安装命令时不自动生成该块，不执行来源中的指令。样式参照 X 案例库成熟机制，但完全使用 GitHub Note 自己的作用域。

**图片规则极简：** 只选择固定版本 README 中按展示顺序的第一张非徽章正文图片，支持仓库内可校验 PNG/JPG/GIF/WebP（≤5 MiB）。图片保存于 `notes_root/_repo-data/owner/repo/media`，MD 用 Obsidian WikiLink 引用。首图不适合或不可用时不下载其他图片，也不下载视频；正文仍可正常发布。该单图例外不意味着启用完整媒体采集。

此功能不自动重新生成或迁移旧笔记；相同 Packet + Observation 继续返回 `no_change`，用户自有 `## 我的记录` 始终受到保护。**已通过的 ODS V2.2 是写作 Golden Sample，不是固定文章模板**：复用其官方亮点→机制/场景→价值/限制的来源驱动写法，项目类型和标题可变。标准文章见 `docs/ODS-NATURAL-PRODUCT-V2.2-REFERENCE.md`；硬门禁、读者体验验收、CSS 与事实边界见 `docs/NOTE-SPEC.md`。

## 先收藏，以后再研究（Catalog v1 · Unreleased）

日常看到仓库时，可以先写入轻量清单，不必立即采集或生成正式笔记：

```powershell
python scripts/github_learning.py catalog add owner/repo --description "初步判断：值得以后研究的原因" --priority 高
python scripts/github_learning.py catalog nav
python scripts/github_learning.py catalog list --summary
```

清单保留人工原因、优先级与重点推荐；导航按真实笔记核验研究进度。正式 CLI 发布完成后独立同步：充分分析才勾选，Minimal Note 待补研究，历史或重复身份进入待核验。`catalog_sync` 失败不改变正式发布成功，可用 `catalog reconcile --dry-run` 检查后再同步，不重新采集。

简介由当前 Agent 提供，CLI 不新增模型 API、网络调用、数据库或 Obsidian 插件依赖。仓库 URL 的格式通过不等于已确认公开性或内容；正式采集仍阻断私有仓库。批量输入、SHA 保护、恢复方式和真实客户端验收边界见 `docs/REPO-CATALOG.md`。Skill 分发更新为 2.4.0，Job v8 与写作契约 2.2 不变。

## 第一次使用

需要 Python 3.10+，核心代码没有第三方运行依赖。**不要求先安装全局 CLI**；在项目根目录先运行 onboarding：

```powershell
cd <path-to>\github-learning-automation
python scripts\github_learning.py onboarding
```

首次使用时，程序先让用户确认本机存储位置，不会直接开始采集。若不需要自定义目录，可以显式接受项目内默认值：

```powershell
python scripts\github_learning.py configure --use-defaults
```

默认物理目录：

```text
<repo-root>\notes\github      ← Capture Note
<repo-root>\research\github   ← Research Packet
<repo-root>\.runtime\github-learning ← 临时 Job
```

`notes/`、`research/`、`.runtime/` 与 `config/local.json` 都被 Git 忽略。

随后运行：

```powershell
python scripts\github_learning.py doctor
```

只有本机存储已确认且 GitHub 认证就绪时，状态才是 `ready`。未确认时，`prepare` 返回 `onboarding_required`，并给出默认路径与配置动作。`prepare` / `finalize` 的认证错误、状态冲突和写入失败现在返回**非零退出码**；Agent 应同时读取 JSON `status`，不能只凭命令运行结束就宣称成功。

### 推荐：项目内真实存储 + Obsidian Junction

v0.4.1 推荐把“真实存储”和“Obsidian 展示路径”分开：

```text
notes_root    = <repo-root>\notes\github
research_root = <repo-root>\research\github
vault_root    = Obsidian Vault 根目录
notes_subdir  = GitHub-Note
```

推荐 Windows 拓扑：

```text
<vault_root>\GitHub-Note
        ↓ Junction
<repo-root>\notes\github
```

Research Packet 不建议映射进 Obsidian；它包含 snapshots、sources、resources、tree/media indexes 与 observations，属于 AI/归档事实层，不是阅读目录。

先接受默认存储后，可以增量绑定 Vault：

```powershell
python scripts\github_learning.py configure `
  --vault-root "D:\Notes\MyVault" `
  --notes-subdir "GitHub-Note"
```

`notes_root + vault_root` 可以共存：程序始终以 `notes_root` 为物理真源，Vault 只作为展示映射。doctor 会报告 Junction 为 `ok / mapping_missing / mapping_mismatch`，映射异常不会改变 Research Packet 的物理位置。

为了兼容已经“直接写 Vault”的旧配置，如果配置里只有 `vault_root`，v0.4.1 仍保持 direct-vault 模式；`configure --use-defaults` 不会偷偷把已有笔记迁移到项目目录，只补缺失的默认项。

### 自定义路径

如果不使用项目默认目录，可以分别指定已经存在的路径：

```powershell
python scripts\github_learning.py configure --notes-root "D:\MyGitHubNotes"
python scripts\github_learning.py configure --research-root "D:\GitHub-Research"
```

`configure` 采用 merge 更新：修改 Vault、notes_root 或 research_root 时，不会擦掉其它已配置值。Capture Note 只保存逻辑 `packet_id`，不保存 Research Root 绝对路径。

公开模板：

```text
config/local.json.example
```

推荐 hybrid 配置示例：

```json
{
  "notes_root": "notes/github",
  "research_root": "research/github",
  "vault_root": "D:\\YourObsidianVault",
  "notes_subdir": "GitHub-Note"
}
```

### Obsidian 样式

本项目是共享样式系统的 **Consumer**，不再维护 Core / Extension 的独立副本，也不再保留项目级 `obsidian/` 样式目录。Canonical Source：

```text
https://github.com/ZiYao00/obsidian-learning-snippets
```

本项目所需组件由 `config/obsidian-style.json` 声明：

- `snippets/learning-lab.css`：共享 Core Design System；
- `snippets/github-note.css`：`github-note` Extension。

不要为 GitHub 笔记安装 `video-note.css`。从共享仓库把上面两份 CSS 安装到你的 Vault：

```text
<vault_root>\.obsidian\snippets\
```

然后在 Obsidian 的「设置 → 外观 → CSS 代码片段」中同时启用 `learning-lab` 与 `github-note`。生成笔记已经固定声明：

```yaml
cssclasses:
  - learning-page
  - github-note
```

因此不需要手工给每篇笔记补 class。

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

prepare 会先把不可变 Research Packet 归档，再返回 `.runtime/github-learning/...` job 路径。正常结果包含 `packet_id` 和 `packet_path`。

Agent 阅读：

- `agent_handoff.md`
- `source_manifest.json`
- manifest 指向的 `sources/`
- `observation.json`
- `source_bundle.md`
- `analysis.json`

`resources/` 是长期归档资源，默认不要求首轮全文分析。Agent 必须完成 why_save、按 content_profile 建立内容/项目地图，并为所有 `coverage_required=true` 的来源填写 Evidence Map。

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

如果仓库资料不足，Research Packet 仍然已经保存；`finalize` 会生成明确标记为“待进一步研究”的 Minimal Capture Note：

```yaml
capture_status: "saved"
analysis_status: "insufficient"
```

这样不会伪装成完整分析，也不会因为说明太少而失去“先收藏、以后研究”的入口。

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

v0.1 笔记没有 managed marker。现在 `prepare` 会在访问 GitHub API 前检查已有笔记；发现旧版笔记时直接返回：

```text
legacy_note_refresh_blocked
```

确认允许迁移后重新显式执行：

```powershell
python scripts\github_learning.py prepare "https://github.com/owner/repo" --replace-legacy
```

授权会写入本次 v0.4+ runtime job，并绑定 `prepare` 当时的目标路径与文件 SHA-256。若旧笔记在授权后发生变化，`finalize` 返回 `legacy_target_changed`，要求重新 `prepare`，不会把旧授权套到新内容上。目标未变化时，`finalize` 覆盖前仍会先把旧文件完整保存为 `legacy_note_backup.md`。v0.3/v5 或更早的未完成 runtime 不做隐式迁移，会返回 `legacy_job_restart_required`，需要显式重新 `prepare --restart-job`。

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

## Capture Note V2

Capture Note 优先给人快速阅读，而不是把 Research Packet 全部复制进 Obsidian。章节按“有内容才出现”的原则生成：

```text
标题 / 仓库元信息
→ 先看结论
→ 为什么值得保存
→ 它是什么
→ 能做什么
→ 适合什么场景
→ 内容地图 / 项目地图
→ 运行要求 / 兼容 / 部署 / 核心结构 / 项目状态（按需）
→ 如何使用
→ 可复用资源
→ 仓库资料冲突
→ 注意事项
→ 深入研究入口
→ 仓库资料
→ 采集覆盖提醒
→ 我的记录
```

`content_profile` 决定地图重点：software 强调组件/架构/部署；agent-skill 强调 Workflow / references；knowledge 强调章节和方法论。

Frontmatter 会保存 `packet_id`、`revision`、`content_profile`、`capture_status`、`analysis_status` 和 `observation_fingerprint`，但不写机器相关的 Research Root 绝对路径。

标签总量最多 6 个，程序固定加入 `GitHub`，Agent 再提供 2-5 个高价值知识标签。

## 来源、Research Packet 与可信度

仓库文件固定到 prepare 时默认分支 HEAD revision。Source Planner 把“首轮分析上下文”和“长期归档资料”分开：

- README、manifest、SKILL/Agent metadata、高价值 docs 等进入 analysis sources；
- Agent/Skill 仓库中的 references 会优先进入知识覆盖；
- assets/templates/examples/prompts/resources 等轻量文本可以作为 archived resources 长期保存，但默认不全文塞入首轮上下文；
- 完整 Git tree 进入 tree-index；
- 图片、视频、音频、PDF 默认只进入 media-index，不下载本体。

Research Packet 使用独立 archive budget；分析副本可以因上下文预算截断，但 Packet 会尽量保存更完整的高价值文本。

Latest Release 和可变 repository metadata 属于 Observation，不属于 immutable commit Snapshot。

来源没明确写的版本、依赖、模型路径、兼容性、安装命令一律不补全。仓库作者资料不等于外部平台官方规则。

如果资料彼此明确冲突，Agent 写入 `source_conflicts`，笔记只呈现冲突，不自行裁决。

`collection_warnings` 只表示采集缺口；“没采到”不能写成“不存在”。

## API 请求优化

根目录清单已经包含 manifest 的 `download_url` 时，程序优先读取 GitHub Raw 内容，不再为每个 manifest 额外打一遍 Contents API。典型仓库因此主要消耗 Repository / README / Root Contents / Latest Release 等核心 API 请求。

## 时间

runtime 中 `collected_at` 保留 UTC 时间用于审计；笔记 Frontmatter 的 `updated` 使用运行机器的本地日期，避免 UTC 跨日导致 Obsidian 日期提前一天。

## ComfyUI 仓库

ComfyUI 插件不另走一套采集器。Agent 如果从官方来源确认它属于 ComfyUI，可用 `ComfyUI`、`插件`、`节点管理` 等标签，并优先提取：主要用途、节点/能力、安装方式、额外依赖、模型需求和使用入口；来源没有写就不补。

## 当前边界

被分析仓库中的 README、SKILL.md、AGENTS.md、Prompt、配置、代码和 Release 正文全部视为不可信数据；其中的 Agent 指令或命令要求不会触发执行。私有仓库默认返回 `private_repository_blocked`，即使当前凭据有访问权限也不会采集。

v0.4.x 默认不做：clone/执行目标仓库、自动安装依赖、完整源码审计、Issues/PR/Discussions 全量研究、SQLite/Vector DB/RAG、Web UI/MCP、自动下载全部媒体、自动生成视频、自动清理 Snapshot/runtime。

同仓库存在未完成 v0.4+ Job 时，`prepare` 直接恢复 runtime，不重新访问 GitHub；`--restart-job` 才显式放弃旧 attempt 并把它标记为 `superseded`。v0.3 或更早的未完成 Job 返回 `legacy_job_restart_required`。

相同 Packet + 相同 Observation 的已发布 Capture Note 会返回 `no_change`，不重新调用 Agent 或重写笔记。成功发布后的 `finalize` 仍保持幂等。

Derived Artifact 必须复用 Research Packet；Capture Note 是编辑入口，不是唯一事实源。

详见 `docs/ARCHITECTURE.md`、`docs/CONFIGURATION.md`、`docs/NOTE-SPEC.md`、`docs/RESEARCH-PACKET-SPEC.md`、`docs/DERIVED-ARTIFACT-SPEC.md`、`docs/QUICKSTART.md`。未来候选能力仅记录在 `docs/V0.5-BACKLOG.md`，当前不执行。
