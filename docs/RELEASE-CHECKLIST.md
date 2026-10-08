# Release Checklist

## 代码与版本

- `pyproject.toml` 与 `github_learning.__version__` 一致。
- USER_AGENT 从包版本派生。
- CHANGELOG 已记录本次版本。
- `config/local.json.example` 覆盖 notes_root + research_root + Vault hybrid 示例，但不包含真实本地路径。
- 无无关文件、本地秘密、Token 或临时测试产物进入提交。
- `temp/run-obsidian-snippets-migration.cmd` 若仍为用户现场未跟踪文件，继续保持排除。

## Research Packet 回归

至少验证：

- `onboarding` 的 action_required / auth_recommended / ready，以及 `prepare` 的 onboarding_required 门禁。
- 新用户默认路径只提示不静默写入；`configure --use-defaults` 创建项目内 `notes/github + research/github`；configure merge 不互相擦除。
- Python、Node/Web、Docker、Agent/Skill、极简仓库 Source Planner 行为。
- 所有仓库文件来源固定到同一 revision。
- private_repository_blocked。
- analysis sources 与 archived resources 分离。
- Packet repository/tree/media 核心 SHA-256 校验。
- source/resource SHA-256 校验。
- same repo@revision + same fingerprint → packet_reused。
- same repo@revision + different fingerprint → packet_conflict。
- Latest Release 存在 observations，不混入 immutable Snapshot。
- failed/partial staging 不自动删除。
- Prompt Injection 文本只作为数据。

## Capture Note / lifecycle 回归

至少验证：

- Job v6：collected → packet_archived → analysis_required → analysis_complete → published。
- v0.4+ in_progress 恢复不重复 GitHub collection。
- v0.3/v5 活动 Job 返回 `legacy_job_restart_required`。
- `--restart-job` 保留旧 Job 并标记 superseded。
- Evidence Map 强制覆盖所有 `coverage_required=true` source。
- 新 sufficient Job 的自然产品解读 `editorial_headline` / `editorial_body` 必填，渲染成一篇连贯文章；旧 Job 兼容原结构，Minimal Note 不变。
- Full Capture Note 保留结构数据（why_save、adaptive map、resource index、packet_id），即使它们不再被机械拼接成章节。
- README 只选首张非徽章正文图片，固定 revision Git blob/size 验证后保存一张，放到阅读层 `_repo-data`；首图失败不下载第二张，不影响文章；无图仓库不配图。
- 仓库 README 有官方功能亮点总览时，正文必须保留有价值的主类别，并以典型场景深化，不按固定七项模板填空；对隐私/无云/遥测等说明保持作者归属和官方联网例外。
- Obsidian `GitHub-Note/_repo-data` 仅通过共享 `github-note.css` 在文件树隐藏，保留本地文件和引用；待整理目录名为 `00-待整理`，不搬迁旧正式笔记。
- `source_status=insufficient` 发布 Minimal Capture Note。
- same Packet + same observation → no_change。
- create / refresh / legacy migration / duplicate note。
- finalize 幂等。
- `## 我的记录` 区域 refresh 后保留。
- ODS V2.2 样板可在 Obsidian 打开，图片 WikiLink 可见；只做单篇试点，不在没验收前重写其他旧笔记。
- 新版 `tests/test_editorial_v22.py` 的标准库测试通过；完整 pytest 套件如环境缺少 pytest 则记录未验证，不擅自安装。

## 代表性真实仓库

- `Osmantic/ODS`：container/software。
- `chenjin-cmd/wechat-graphic-monetization`：Agent/Knowledge Skill，references + archived assets。
- `psf/requests`：Python project，Capture Note 保持紧凑。
- `octocat/Hello-World`：极简仓库，可验证 Minimal Capture Note。

真实 smoke 因网络失败时应区分 timeout 与实现回归；保留本地 synthetic 验证结果，不把网络错误当代码失败。

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
