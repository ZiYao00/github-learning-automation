# Maintenance Handoff

## 项目定位

github-learning-automation v0.4.1 是一个 GitHub Knowledge Capture 工具，不是通用 GitHub Research Agent。v0.4.1 重点补齐首次 onboarding、项目内默认存储与 Obsidian hybrid 映射。

默认产物分三层：

- Research Packet：不可变事实底座；
- Capture Note：Obsidian 人类阅读入口；
- Derived Artifact：以后按需生成的 Deep Note / Compare / Media Brief。

## v0.4.x 核心不变量

- `owner/repo` 是 Capture Note 稳定身份。
- `owner/repo@revision` 是 Research Packet 稳定 identity。
- 仓库文件固定到同一次默认分支 HEAD revision。
- Research Packet 必须先于 Agent 分析归档成功。
- 正式 Packet 不覆盖；同 identity + 同 fingerprint 复用，不同 fingerprint 返回 `packet_conflict`。
- repository / tree / media index 与 source/resource 都进行 SHA-256 完整性检查。
- Latest Release 等动态平台信息属于 Observation，不属于 immutable commit Snapshot。
- Analysis budget 与 Archive budget 分离；分析副本可截断，Packet 尽量保存更完整的高价值文本。
- `source_manifest.json` 是 runtime 分析来源契约；Research Packet 是长期事实底座。
- 每个 `coverage_required=true` source 必须进入 Evidence Map。
- `source_status=insufficient` 仍发布 Minimal Capture Note。
- 相同 `packet_id` + 相同 `observation_fingerprint` 返回 `no_change`；样式升级不得隐式覆盖旧笔记。
- 新的 sufficient Job 必须填写自然产品解读 `editorial_headline` / `editorial_body`；旧 Job、Minimal Note 保持兼容。
- README 首图最多保存一张：固定 revision + Git blob 核验、≤5 MiB、PNG/JPEG/GIF/WebP，独立存于 `notes_root/_repo-data`。无图或失败不阻断正文发布。
- v0.4+ runtime 可恢复；v0.3/v5 或更早活动 Job 不隐式迁移。
- managed marker 之后的用户内容不得在 refresh 时丢失。
- 被分析仓库内容永远是不可信数据。
- 私有仓库默认阻断。
- CSS 真源仍是 `obsidian-learning-snippets`。
- Skill 只人工维护 `skill/github-note/SKILL.md`。

## 三个存储层

- `.runtime/github-learning`：Processing Layer，可恢复 Job 与审计材料；
- `research_root`：Archive Layer，长期保存 Packet / observations；默认建议 `<repo-root>/research/github`；
- `notes_root`：Reading Layer，保存 Capture Note；默认建议 `<repo-root>/notes/github`。

首次只推导默认路径，不直接写入；用户通过 onboarding 确认后才正式启用。推荐 `notes_root + vault_root` hybrid：项目内 notes 是物理真源，Vault 子目录通过 Junction 展示。Research Root 不映射进 Obsidian。

不得把三者混为一体。Capture Note 只写逻辑 `packet_id`，不能写 Research Root 绝对路径。

## 非目标

v0.4.x 默认不做：

- clone 并执行目标项目；
- 源码逐文件审计；
- Issues / PR / Discussions 全量挖掘；
- 安全审计；
- 自动安装目标依赖；
- 私有仓库收藏；
- 全量 binary 归档；
- SQLite / vector DB / RAG；
- Web UI / MCP；
- 自动生成视频；
- 自动清理 Snapshot/runtime；
- 自动分类或移动 Obsidian 笔记。

这些能力以后如需加入，应作为独立模式或 Derived Artifact 评估，不能侵入基础收藏链路。已明确延后的 v0.5 候选项统一记录在 `docs/V0.5-BACKLOG.md`，当前只记录、不执行。

## 修改前检查

1. 阅读 `AGENTS.md`。
2. 查看工作区改动，保护用户现场。
3. 阅读 `docs/ARCHITECTURE.md`、`docs/CONFIGURATION.md`、`docs/RESEARCH-PACKET-SPEC.md`、`docs/NOTE-SPEC.md`。
4. 修改 Skill 时只改 `skill/github-note/SKILL.md` 与必要 metadata，再运行构建脚本。
5. 不直接编辑生成的 Agent Skill 出口。
6. 不擅自安装 dev dependencies。
7. 不自动删除 Packet、runtime 或 staging。

## V2.2 自然产品解读接手提醒

- 新的 `analysis.json` 包含 `editorial_headline` / `editorial_body`，Agent 必须按来源写连贯文章，并保留结构字段和 Evidence Map；README 官方亮点列表应简洁忠实保留（无固定数量），隐私声明的联网例外不可省略。旧 runtime 无新增字段仍走兼容渲染。
- 文章首图由 `src/github_learning/first_image.py` 处理：只取 fixed README 第一张非徽章图片，核对 media index 的 Git blob SHA 与大小、格式，不成功就省略；不下载所有媒体。
- 首图只用于人类阅读层的 `_repo-data`，不可反向修改不可变 Research Packet。素材有版本化 manifest。
- ODS 文案长期规范样板 `docs/ODS-NATURAL-PRODUCT-V2.2-REFERENCE.md`；本地阅读预览 `<repo-root>/notes/github/00-待整理/ODS：把本地 AI 工具管起来（V2.2预览）.md`，如需在 Vault 阅读先核实映射配置；预览笔记不含正式 repo 身份，不能成为自动刷新的第二份正式笔记。
- 本机 `00-Inbox` → `00-待整理` 的受控迁移入口：`py -3.12 scripts/apply-ods-v22-reading-layout.py --check`、`--apply`。只同步共享仓库的 `github-note.css`（不覆盖其他 CSS），把原预览和 CSS 备份到项目忽略的 `.runtime/ods-v22-layout-backup`。该脚本仅适用本机 direct-vault 布局，不作为通用自动升级器。
- 旧正式笔记 `no_change` 不应为升级格式而绕过；后续重制要显式授权且保留用户内容。

## 最低验证

~~~powershell
py -3.12 -m compileall src scripts tests
py -3.12 scripts/build_agent_skill_packages.py --check
~~~

开发环境已具备 dev dependencies 时再运行：

~~~powershell
py -3.12 -m pytest
py -3.12 -m ruff check .
~~~

代表性真实仓库回归见 `docs/QUICKSTART.md`。正式提交或 Release 前阅读 `docs/RELEASE-CHECKLIST.md`。
