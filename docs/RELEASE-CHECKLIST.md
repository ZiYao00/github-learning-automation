# Release Checklist

## 代码与版本

- `pyproject.toml` 与 `github_learning.__version__` 一致。
- USER_AGENT 从包版本派生。
- CHANGELOG 已记录本次版本。
- `config/local.json.example` 覆盖 notes_root + research_root + Vault hybrid 示例，但不包含真实本地路径。
- 无无关文件、本地秘密、Token 或临时测试产物进入提交。
- `temp/run-obsidian-snippets-migration.cmd` 若仍为用户现场未跟踪文件，继续保持排除。
- CLI 的 `auth_invalid` / `private_repository_blocked` / `ConfigurationError` 及未知阻断状态应返回非零；可用 `tests/test_cli_exit_codes.py` 的无网络单元测试确认。

## Research Packet 回归

至少验证：

- `onboarding` 的 action_required / auth_recommended / ready，以及 `prepare` 的 onboarding_required 门禁。
- 新用户默认路径只提示不静默写入；`configure --use-defaults` 创建项目内 `notes/github + research/github`；configure merge 不互相擦除。
- Python、Node/Web、Docker、Agent/Skill、极简仓库 Source Planner 行为；通用 `*_PROMPT.md`、`PROMPTS.md`、`README_ZH.md` 的来源选择与优先级回归。
- 所有仓库文件来源固定到同一 revision。
- private_repository_blocked。
- analysis sources 与 archived resources 分离。
- Packet repository/tree/media 核心 SHA-256 校验。
- source/resource SHA-256 校验。
- same repo@revision + same fingerprint → packet_reused。
- same repo@revision + different fingerprint → packet_conflict，不覆盖原 Packet。若只是 Source Planner 升级，原固定版本已归档来源需被优先重用，正常 `no_change`；额外作者原文只能通过 SHA 核验的 append-only supplements 获取。
- Latest Release 存在 observations，不混入 immutable Snapshot。
- failed/partial staging 不自动删除。
- Prompt Injection 文本只作为数据；`supplemental_evidence` 必须验证路径、固定提交、Git Blob SHA、内容 SHA256 及原 Packet 绑定，篡改需拒绝。

## Job v8 / 可靠性负向门禁

- v8 `evidence_set_id` 与已归档 Packet + 补证 manifest hash 一致；同提交新增补证返回 `update_available`，需 `--refresh-evidence` 明确允许后才更新现有笔记。
- 主来源 Git Blob SHA、字节大小、UTF-8 严格核验；新 Packet 带 archive seal，历史 V1 仍可只读验证；Source Planner 超过预算需输出候选来源遗漏提示。
- 禁止 `superseded`、`packet_archive_failed`、未知状态和缺失证据 Job 发布；CLI 错误退出码必须非零。
- 两个 Agent 同时对同一 repo 发布，OS 锁防冲突；新建独占、刷新目标 SHA 不符则拒绝；人工记录 `## 我的记录` 完整保留。
- 写入目标后状态未更新的中断可核验事务后恢复；未写入目标时可安全重试；缓存的 `note_ready` 应确认目标存在与内容未变。
- 无来源或篡改的 `~~~prompt` 块、`gh-source` 引用必须拒绝；HTML 图片、音视频、Markdown 引用式图片与不安全标签不能混入正文；代码字面示例合法。
- `tests/test_publish_safety.py`、`test_evidence_v8.py`、`test_git_blob_verification.py`、`test_editorial_integrity.py`、`test_pinned_supplement.py` 均需通过，不推断缺少的 pytest 套件已通过。

## Capture Note / lifecycle 回归

至少验证：

- 新 Job v8（契约 2.2）：collected → packet_archived → analysis_required → analysis_complete → published；旧 v6 Job 可原状态恢复。
- v0.4+ in_progress 恢复不重复 GitHub collection。
- v0.3/v5 活动 Job 返回 `legacy_job_restart_required`。
- `--restart-job` 保留旧 Job 并标记 superseded。
- Evidence Map 强制覆盖所有 `coverage_required=true` source。
- 新 v8 sufficient Job 的自然产品解读 `editorial_headline` / `editorial_body` 必填，且五项 `editorial_review` 通过；旧 Skill 提交缺字段/旧格式必须被阻断，不能退回旧模板。旧 v6 Job 兼容原结构，Minimal Note 不变。
- Full Capture Note 保留结构数据（why_save、adaptive map、resource index、packet_id），即使它们不再被机械拼接成章节。
- README 只选首张非徽章正文图片，固定 revision Git blob/size 验证后保存一张，放到阅读层 `_repo-data`；首图失败不下载第二张，不影响文章；无图仓库不配图。
- 以已通过的 `docs/ODS-NATURAL-PRODUCT-V2.2-REFERENCE.md` 为 Golden Sample，复用问题导向与事实核查的写法而非 ODS 固定结构；`docs/NOTE-SPEC.md` 的硬性门禁全部通过后才批准 sufficient。
- 仓库 README 有官方功能亮点总览时，正文必须保留有价值的主类别，并以典型场景深化，不按固定七项模板填空；对隐私/无云/遥测等说明保持作者归属和官方联网例外。
- CSS v0.4 在原编辑式阅读基础上按需支持 `gh-source` 官方逐字原文引用和 `prompt` 原始 Prompt 代码框，必须验证来源核对、翻译标注、原生复制按钮、320px 滚动、长文本换行、深浅色和窄视口；只有普通源码/安装命令时不得伪装为 Prompt。
- CSS 采用 GitHub Note 专属编辑式阅读增强：检查 ODS / 非 ODS 旧笔记、深浅主题、窄窗口、原生源码/Live Preview、首图、文件树隐藏；关闭 CSS 后 Markdown 仍完整可读。共享仓库的 `scripts/qa_github_note_reading.py` 为十场景静态 QA，不能取代真实 Obsidian 客户端验收。
- Obsidian `GitHub-Note/_repo-data` 仅通过共享 `github-note.css` 在文件树隐藏，保留本地文件和引用；待整理目录名为 `00-待整理`，不搬迁旧正式笔记。
- `source_status=insufficient` 发布 Minimal Capture Note。
- same Packet + same observation + same verified evidence_set_id → no_change；新增合法补证 → update_available（不得静默覆盖）。
- create / refresh / legacy migration / duplicate note。
- finalize 幂等。
- `## 我的记录` 区域 refresh 后保留。
- ODS V2.2 样板可在 Obsidian 打开，图片 WikiLink 可见；只做单篇试点，不在没验收前重写其他旧笔记。
- 新版 `tests/test_editorial_v22.py` 的标准库测试通过；完整 pytest 套件如环境缺少 pytest 则记录未验证，不擅自安装。

## Job v8 隔离真实仓库验收

- `py -3.12 scripts/smoke_v8_isolated.py prepare` 仅在用户同意真实 GitHub 获取后执行；固定 `psf/requests` 并写入被忽略的 `.runtime/closeout-v8/`，不使用实际 Vault。
- Agent 根据该 Job 的 README、Quickstart、Install、Security、FAQ 和非必审 pyproject 原文分析，保存 `analysis.json`，再用同一脚本的 `finalize <job_dir>` 与 `verify <job_dir>` 校验 `note_ready`、`evidence_set_id`、幂等 finalize、重复 prepare 返回 `no_change`。绝不执行目标仓库代码。
- `agent_handoff.md` 应明确当前新 Job v8 / 写作 V2.2 / `evidence_set_id`，不能错误注明 v7。真实仓库及隔离 Job 的运行结果不得当作已有 Obsidian 界面人工验收的替代。
- 若当前开发环境没有 `pytest` / `ruff`，记录“完整测试未执行”并等待依赖安装授权；不得用若干标准库专项测试宣称全量通过。

## 代表性真实仓库

- `Osmantic/ODS`：container/software。
- `chenjin-cmd/wechat-graphic-monetization`：Agent/Knowledge Skill，references + archived assets。
- `psf/requests`：Python project，Capture Note 保持紧凑。
- `octocat/Hello-World`：极简仓库，可验证 Minimal Capture Note。

真实 smoke 因网络失败时应区分 timeout 与实现回归；保留本地 synthetic 验证结果，不把网络错误当代码失败。
- 新联动验收：`liyue-aigc/seedance-2-5-video-director` 固定 revision `ad0e68ba6ce24fb9ae9c67c9276061cef37663f1`，10 来源、Job v7 / 契约 2.2、发布于 `00-待整理`、`first_image_status=no_image`、复次 prepare 返回 `no_change`；可用本机集成脚本 `py -3.12 scripts/verify_seedance_v22_smoke.py` 复核原始 Prompt 保真与文献归属。不能把这一次成功等同于所有 Agent 语义质量自动保证。

## Agent 与文档

~~~powershell
py -3.12 scripts/build_agent_skill_packages.py
py -3.12 scripts/build_agent_skill_packages.py --check
~~~

确认以下内容互不矛盾：

- `AGENTS.md`
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/CONFIGURATION.md`
- `docs/RESEARCH-PACKET-SPEC.md`
- `docs/NOTE-SPEC.md`
- `docs/DERIVED-ARTIFACT-SPEC.md`
- `docs/QUICKSTART.md`
- `docs/V0.5-BACKLOG.md`
- `skill/github-note/SKILL.md`
- 派生 `references/NOTE-SPEC.md`、`ODS-V2.2-GOLDEN.md`、`contract.json` 与 `release/skill.zip` 哈希一致；网页旧 Skill 必须重新安装，不得假设自动覆盖。

## 自动验证

最低可执行验证：

~~~powershell
py -3.12 -m compileall src scripts tests
py -3.12 scripts/build_agent_skill_packages.py --check
~~~

如果本机已经安装 dev dependencies，再运行：

~~~powershell
py -3.12 -m pytest
py -3.12 -m ruff check .
~~~

不得为了满足测试自动安装依赖。

## GitHub 发布

Release 属于独立授权动作。只有用户明确要求时才：

- commit；
- push；
- 创建 tag；
- 创建 GitHub Release。

v0.4.1 正式 Release 前还应检查 GitHub Description、License、README、默认目录 onboarding 行为与公开仓库预期。
