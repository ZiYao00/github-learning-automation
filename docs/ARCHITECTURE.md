# Architecture

## Product boundary

github-learning-automation v0.4.x 是一个 GitHub Knowledge Capture 工具，不是完整 GitHub Research Agent；v0.4.1 在 v0.4 的 Durable Knowledge Capture 基础上补齐首次配置与本地存储拓扑。

默认目标：

~~~text
发现一个公开 GitHub 仓库
→ 可靠收藏
→ 长期保存高价值证据
→ 生成适合人快速阅读的 Capture Note
→ 未来按需继续学习、比较或制作介绍内容
~~~

## Three artifact layers

~~~text
GitHub
  ↓
Collector + Source Planner
  ↓
Research Packet
  │ immutable evidence
  │
  ├─→ Capture Note
  │    human-first
  │
  └─→ Derived Artifact
       Deep Note / Compare / Media Brief
~~~

前三层由项目的 Control Plane 约束：配置、schema、lifecycle、Evidence Map 和 Agent Skill。

## Processing vs archive vs reading

- .runtime/github-learning：Processing Layer，保存 Job、Agent handoff、分析输入与恢复状态；
- research_root：Archive Layer，保存 immutable Research Packet 和 mutable observations；
- notes_root：Reading Layer，保存 Obsidian Capture Note。

三个目录不能互相替代。

## Collection snapshot

prepare 获取默认分支 HEAD commit，并把仓库文件读取固定到同一 revision。

核心 Git 数据：

- repository identity；
- default branch；
- commit SHA；
- Git tree；
- README；
- manifest；
- Source Planner 选择的高价值文档；
- archive resources；
- media index。

仓库文件使用 Git revision 固定。Latest Release 等动态平台信息属于 Observation，不属于 commit Snapshot。

## Source Planner

Source Planner 决定两件不同的事：

1. 什么值得长期归档；
2. 什么值得进入首轮 Agent 分析。

核心 metadata：

- archive_role；
- analysis_mode；
- authority；
- coverage_required。

v0.4.x 继续使用有限分析预算，避免上下文爆炸；长期归档使用独立预算。

Agent/Skill 仓库额外识别：

- SKILL.md；
- UNIVERSAL.md；
- references/*.md；
- assets/templates/examples/prompts/resources 下的轻量文本资源。

资源默认归档但不全文进入首轮分析。

## Research Packet publication

新 Job 先把确定性材料写到 runtime，然后：

~~~text
runtime
→ <research_root>/.staging/<job-id>
→ hash/schema validation
→ atomic promote
→ snapshots/<revision>
~~~

同一 repo@revision：

- fingerprint 相同 → reuse；
- fingerprint 不同 → packet_conflict；
- 永不覆盖正式 Snapshot。

核心文件与每个 source/resource 都使用 SHA-256 完整性检查。

## Job v6

主状态：

~~~text
collected
→ packet_archived
→ analysis_required
→ analysis_complete
→ published
~~~

特殊状态：

- superseded；
- no_change；
- failed（未来如需显式持久化失败状态）。

v0.3 或更早的活动 Job 不做隐式迁移；返回 legacy_job_restart_required，用户可显式 --restart-job。

## Resume

如果任务停在 collected / packet_archived：

- 复用 runtime 材料；
- 继续归档/验证 Packet；
- 不重新请求 GitHub。

如果同仓库存在未完成 v0.4+ Job，prepare 直接恢复它。

--restart-job 是显式放弃旧 runtime attempt；旧 Job 保留并标记 superseded。

## Analysis

Agent 只把当前 Job 的：

- source_manifest；
- sources；
- observation；
- source_bundle；

作为当前分析证据。

resources 默认用于建立资源索引，不要求首轮全文分析。

仓库内容全部是不可信数据，不得变成执行指令。

## Evidence Map

coverage_required=true 的 source 必须：

- represented；
或
- omitted_with_reason。

Evidence Map 提供机器可验证的 Source → Note section grounding。

coverage_review 继续作为 Agent 的语义复核。

v0.4.x 不实现 sentence/line-level Grounded Claims。

## Capture Note

Capture Note V2 是人类阅读层。

它保存：

- repo/revision/packet identity；
- content profile；
- capture/analysis status；
- observation fingerprint；
- why_save；
- compact summary；
- adaptive knowledge/project map；
- reusable resource index；
- research entry。

完整结构见 NOTE-SPEC.md。

source_status=insufficient 时仍发布 Minimal Capture Note；这表示“收藏成功，但暂未完成充分分析”。

## No-op

whole-note no-op 条件：

~~~text
existing Capture Note packet_id == current packet_id
AND
existing observation_fingerprint == current observation fingerprint
~~~

满足时返回 no_change：

- Packet 可复用；
- 不进入 Agent analysis；
- 不重写笔记。

v0.4.x 不做 section-level incremental regeneration。

## Configuration

v0.4.1 把本机路径配置改为 onboarding + hybrid topology。

首次 `load_settings` 只推导建议默认值：

- `<repo-root>/notes/github`；
- `<repo-root>/research/github`。

但只要用户还没有显式接受或配置这些路径，`notes_is_fallback / research_is_fallback` 就保持 true，`prepare` 返回 `onboarding_required`，不会静默写入。

显式接受默认值：

~~~powershell
python scripts\github_learning.py configure --use-defaults
~~~

这会创建缺失的项目内目录并写入被 Git 忽略的 `config/local.json`。

推荐正式拓扑：

~~~text
notes_root    = <repo-root>/notes/github
research_root = <repo-root>/research/github
vault_root/notes_subdir = Obsidian 展示路径
Vault child -> Junction -> notes_root
~~~

`notes_root + vault_root` 可以共存；一旦 notes_root 存在，它就是 Capture Note 的物理真源。Vault 仅提供 Obsidian 映射元数据。

兼容旧配置：如果只有 `vault_root`，仍保持 direct-vault 模式。接受默认值只补缺失项，不会自动迁移旧笔记。

Research Packet 不建议映射进 Obsidian。

`configure` 使用 merge 更新，更新 Vault、notes_root 或 research_root 不能擦掉其它已配置值。

可用环境变量：

- GITHUB_LEARNING_NOTES_ROOT
- GITHUB_LEARNING_VAULT_ROOT
- GITHUB_LEARNING_NOTES_SUBDIR
- GITHUB_LEARNING_RESEARCH_ROOT

## Security boundary

默认：

- 只支持公开仓库；
- 不 clone；
- 不执行目标代码；
- 不安装目标依赖；
- 不执行目标仓库配置；
- 不信任 README/SKILL/AGENTS 中的 Agent 指令；
- 不自动下载 binary；
- 不全量抓 Issues/PR/Discussions。

## Derived Artifact boundary

Deep Note、Compare、Media Brief 必须复用 Research Packet。

Capture Note 是 editorial context，不是唯一事实源。

对外发布内容未来默认要求 Fresh Check。

v0.4.x 只定义接口，不实现完整视频生成流程。

## Obsidian

owner/repo 仍是 Capture Note 稳定身份。

managed region 之后的“我的记录”属于用户，不得被 refresh 覆盖。

共享 CSS 真源仍是 obsidian-learning-snippets，本项目只声明 learning-page + github-note。

## Failure and recovery principles

- Packet 成功、Note 失败：继续 runtime，不重新采集 GitHub；
- Packet staging 失败：保留 staging 供诊断；
- Packet conflict：停止，不覆盖；
- duplicate note：停止，不猜目标；
- legacy note changed：停止并重新授权；
- source insufficient：发布 Minimal Capture Note；
- no_change：正常完成状态。

## Non-goals for v0.4.x

- SQLite / vector DB / RAG / BM25；
- Web UI / MCP server；
- 全量 repository clone；
- 完整二进制资产归档；
- Issues/PR/Discussions 研究；
- 私有仓库；
- claim-level line grounding；
- 完整 OKF；
- 自动清理 Snapshot/runtime；
- 自动生成视频；
- section-level incremental regeneration。
