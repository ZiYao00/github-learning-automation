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
- 相同 `packet_id` + 相同 `observation_fingerprint` + 相同 `evidence_set_id` 才返回 `no_change`；新增可核验补证先返回 `update_available`，样式升级不得隐式覆盖旧笔记。
- 新 Job v8 写作契约 `editorial_contract_version=2.2`：sufficient 必须填写 `editorial_headline` / `editorial_body`、五项 `editorial_review` 和 Evidence Map，防止旧版 Skill 静默退回章节模板；旧 v6/v7 Job、Minimal Note 保持兼容。
- README 首图最多保存一张：固定 revision + Git blob 核验、≤5 MiB、PNG/JPEG/GIF/WebP，独立存于 `notes_root/_repo-data`。无图或失败不阻断正文发布。
- v0.4+ runtime 可恢复；v0.3/v5 或更早活动 Job 不隐式迁移。
- managed marker 之后的用户内容不得在 refresh 时丢失。
- 被分析仓库内容永远是不可信数据。
- 私有仓库默认阻断。
- CSS 真源仍是 `obsidian-learning-snippets`。
- Skill 只人工维护 `skill/github-note/SKILL.md`。正式规范在 `docs/NOTE-SPEC.md`，唯一黄金样板在 `docs/ODS-NATURAL-PRODUCT-V2.2-REFERENCE.md`；通过脚本将两份文档与契约 JSON 同步进所有 Skill，并校验实际 ZIP。

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

## v8 可靠性增强：修改与回滚边界

- 最新流程只修改主项目 `github-learning-automation`；ODS V2.2 黄金样板、`obsidian-learning-snippets`、历史 Vault 笔记、`## 我的记录`、旧 Research Packet 与其它未提交文件保持原样。
- 新 Job v8 保留写作契约 V2.2；新增 `evidence_set_id`、`publish_transaction.json`，先拿 `owner/repo` 级 OS 文件锁，再进行目标文件 SHA 校验和安全发布。中断后的 `publishing` 状态恢复时只核对事务结果，不能无条件写第二次；失败与 superseded Job 不得发布。
- GitHub 原文先核对 Git Blob SHA / bytes，Packet V1 新归档带可选 archive seal；旧 Packet 仍可验证并从其固定 source/resource 列表优先重采，避免 Source Planner 升级与历史归档冲突。大仓库未纳入的候选来源有明确警告。
- 附加补证不再隐式更新现有笔记：新的有效证据集合使 `prepare` 返回 `update_available`，需用户显式使用 `--refresh-evidence` 进行新一轮分析。只支持自动选择**唯一**补证组；多组返回 `supplement_selection_required`，不可暗中组合。补证清单依然不修改原 Packet。
- V8 `editorial_body` 的 `prompt` 代码框和 `gh-source` 引用，程序根据固定来源原文执行内容匹配；其它媒体的 HTML、引用式图片及 Obsidian 嵌入被拒绝。程序检查不能替代人工判断功能真实性与文章可读性。
- 回归入口：`py -3.12 -m unittest discover -s tests -p test_publish_safety.py -q`、`test_git_blob_verification.py`、`test_evidence_v8.py`、`test_editorial_integrity.py`、`test_cli_exit_codes.py`，以及原有 V2.2/历史兼容/Skill 包检查。无 dev dependencies 不擅自安装。
- 可回滚 Python 代码，但不得自动删除已经写入的补证、事务记录、Snapshot 或 Vault 笔记；如果发布中断需根据事务记录核对目标文件及 hash。暂不引入数据库和跨机器分布式锁；OS 锁保护遵循统一 CLI 的本机 Agent，不替代对其他编辑器的协作约定。

## 本地收尾与隔离的真实 v8 验收

- CLI 对预期的 `analysis_required`、`note_ready`、`no_change`、`update_available` 继续返回 0；认证失败、私有仓库阻断、状态冲突、缺少配置、发布失败及其它异常统一返回非零。回归：`tests/test_cli_exit_codes.py`（全部模拟，不访问 GitHub/用户文件）。
- 真实公开仓库 `psf/requests@611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60` 已完成一次隔离 v8 `prepare → 固定来源人工分析 → finalize → no_change` 流程。脚本 `scripts/smoke_v8_isolated.py` 的所有产物保存在 `.runtime/closeout-v8/<run>/`，绝不写入真实 Vault，也不安装或执行目标仓库代码。作者内容按照 v8 的正式规范复核。
- 真实 Job 的 `agent_handoff.md` 必须随 `CURRENT_JOB_VERSION` 输出 v8，而不能沿用固定“新 Job v7”。回归检查位于 `tests/test_editorial_contract_v7.py`（文件名历史保留）。
- 完整 `pytest` 与 `ruff` 依赖来自 `pyproject.toml` 的可选开发组。本机 Python 3.12 若未安装，必须明确标为“尚未验证”；不未经授权全局安装或擅自宣称 CI 全通过。提交前仅精确暂存仓库代码、规范和测试，`temp/`、本地配置、`.runtime` 和 Research / Vault 数据必须排除。

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
- 已通过、包含 `gh-source` 视觉增强的 ODS V2.2 是写作 Golden Sample（`docs/ODS-NATURAL-PRODUCT-V2.2-REFERENCE.md`）；硬门禁、跨类型适配和编辑式阅读 CSS 契约在 `docs/NOTE-SPEC.md`，不额外维护第二份评分体系。
- 旧正式笔记 `no_change` 不应为升级格式而绕过；后续重制要显式授权且保留用户内容。

## GitHub Note v0.4 组件适配与本机验收（独立共享仓库）

- 按需插入 `> [!gh-source]` 或 `~~~prompt`；前者只呈现 pinned 原文（附译文需清楚标示），后者只展示已核实完整的作者原始 Prompt，并使用 Obsidian 原生 Copy Code。详情见 `docs/NOTE-SPEC.md`。不要修改 `x-case-note.css` 或 X 的数据模型。

- 权威 CSS 文件：`../obsidian-learning-snippets/snippets/github-note.css` v0.4；消费者不要另存可编辑 CSS 副本。仅 GitHub Note Extension 变化；共享 Core 和 X-case CSS 不动。
- 基于 Chrome 的 10 场景静态 QA（原 ODS/旧笔记六组 + ODS pinned 原文引用、真实 Seedance 导演 Skill Prompt 各两组）：`py -3.12 ../obsidian-learning-snippets/scripts/qa_github_note_reading.py`。脚本使用 ODS Golden Sample 和一篇旧式 `bili-learning-automation` 笔记，覆盖亮/暗、宽/窄，核对 H1 > H2、单图、无横向溢出与不覆盖阅读宽度。其输出是**模拟 Obsidian 的样式 DOM**，并非真实 Obsidian 客户端截图。
- 当前本机直连 Vault 的一次性受控单 CSS 同步：`py -3.12 scripts/sync_github_note_editorial_css.py --check` 后运行 `--apply`。仅允许从已验证的 v0.3 哈希升级至 v0.4 共享 CSS 真源；会备份原文件并检查三个其它 snippet 的 SHA-256。以后升级不得直接复用脚本中的旧版哈希基线而跳过检查。
- 双组件的独立本地预览可由 `py -3.12 scripts/publish_github_v04_style_preview.py --check` 预检查，然后 `--apply` 创建到 `GitHub-Note/00-待整理/【视觉验收】GitHub Note v0.4 原文与Prompt（可删除）.md`。只引用固定 ODS README 与真实 Seedance Director 仓库的本地来源；不生成第二份正式 Capture Note。已有同名但内容不同的文件会拒绝覆盖。验收后可以人工删除这一个预览文件。
- 打开 Vault 中的 ODS、v0.4 临时预览和旧版 GitHub Note，用用户当前 Obsidian 主题、阅读宽度插件与 Live Preview 检查真实表现；原生复制按钮应能复制完整 Prompt（Chrome 静态 QA 不能验证剪贴板）。无法进入 GUI 时，应如实标记“客户端视觉验收待确认”。关闭 `github-note.css` 应只撤销视觉增强，不影响笔记内容/图片路径。

## CodexPro V2.2 真实仓库测试发现与修复

- 测试仓库 `rebel0789/codexpro@113472c6ff0a1516b6f223a43cd355abdf2e61ae`：首次 Packet 归档 10 份来源，Source Planner 漏选 `CHATGPT_PROMPT.md`、`CODEX_PROMPT.md` 与 `README_ZH.md`。已增加通用 Prompt/语言变体文档识别，回归测试 `tests/test_prompt_source_planner.py`。
- **不可变快照后置修复**：使用 `scripts/collect_pinned_supplement.py` 按原提交核对 Git Blob SHA 保存补充证据，主 Packet 不修改。若新 Source Planner 对同一提交选出更多来源，`lifecycle._reuse_immutable_source_selection` 优先保留原先 Packet 的来源集合并确保哈希一致，再走 `no_change`；失败的旧中间 Job 保留、只标记为 `packet_archive_failed`。相关用例在 `tests/test_editorial_contract_v7.py` 和 `tests/test_pinned_supplement.py`。
- 真实阅读笔记在 `GitHub-Note/00-待整理/codexpro.md`；两份可复制 Prompt 来自 Git Blob 校验的补证目录，并非那 10 份原 Packet。只读验证：`py -3.12 scripts/verify_codexpro_v22_smoke.py`，检查主 Packet 身份、补证哈希、Prompt 逐字一致、Frontmatter、用户记录和 SVG 首图未下载。再次 `prepare https://github.com/rebel0789/codexpro` 返回 `no_change`。
- 已安装网页版旧 Skill 不会自动更新。对接 ChatGPT/Codex/Claude/WorkBuddy 前先通过 `doctor` 比对 `workflow_skill_version`、`new_job_version` 和 `editorial_contract_version`，构建 `release/skill.zip` 后重新安装，避免使用不懂补证来源的旧指令。

## 新链接端到端验收与可移植回归

- 2026-10-09 已从 GitHub URL 真实采集 `liyue-aigc/seedance-2-5-video-director@ad0e68ba6ce24fb9ae9c67c9276061cef37663f1`：10 份来源，Job v7、契约 2.2、Agent/Skill 正文及完整来源 Prompt；`finalize=note_ready`、`first_image_status=no_image`，第二次 prepare 返回 `no_change`。正式笔记位于已配置 Vault 的 `00-待整理`。可运行 `py -3.12 scripts/verify_seedance_v22_smoke.py` 进行只读核验。
- **可移植单元测试**：`py -3.12 -m unittest discover -s tests -p test_editorial_contract_v7.py -q`、`test_editorial_v22.py`、`test_skill_distribution.py`；ODS README 七项能力的离线回归素材收敛于 `tests/fixtures/ods_readme_features_excerpt.md`，不读取被 Git 忽略的真实 Packet。完整 `pytest` 仍需在已安装相应 dev dependency 的环境执行，禁止未经授权自动安装。
- **人工质量与跨 Agent 边界**：程序阻止新 Job 旧模板回退，但无法证明文笔一定达到 ODS 或其他独立 Agent 已安装新版 Skill；网页版 ChatGPT 的旧 Skill 需要手动重新安装 `release/skill.zip`，再比较 `doctor` 与 Skill `references/contract.json` 的版本。真实 Obsidian 界面复制行为需客户端人工确认。

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
