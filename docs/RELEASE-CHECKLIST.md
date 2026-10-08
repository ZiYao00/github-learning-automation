# Release Checklist

## 代码与版本

- `pyproject.toml` 与 `github_learning.__version__` 一致。
- USER_AGENT 从包版本派生。
- CHANGELOG 已记录本次版本。
- `config/local.json.example` 覆盖 note destination + research_root，但不包含真实本地路径。
- 无无关文件、本地秘密、Token 或临时测试产物进入提交。
- `temp/run-obsidian-snippets-migration.cmd` 若仍为用户现场未跟踪文件，继续保持排除。

## Research Packet 回归

至少验证：

- `doctor` 的 configuration_required / auth_recommended / ready。
- notes 与 research_root 都是显式配置门禁；configure merge 不互相擦除。
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
- v0.4 in_progress 恢复不重复 GitHub collection。
- v0.3/v5 活动 Job 返回 `legacy_job_restart_required`。
- `--restart-job` 保留旧 Job 并标记 superseded。
- Evidence Map 强制覆盖所有 `coverage_required=true` source。
- Full Capture Note 包含 why_save、adaptive map、resource index、packet_id。
- `source_status=insufficient` 发布 Minimal Capture Note。
- same Packet + same observation → no_change。
- create / refresh / legacy migration / duplicate note。
- finalize 幂等。
- `## 我的记录` 区域 refresh 后保留。

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
- `docs/RESEARCH-PACKET-SPEC.md`
- `docs/NOTE-SPEC.md`
- `docs/DERIVED-ARTIFACT-SPEC.md`
- `docs/QUICKSTART.md`
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

v0.4 第一次正式 Release 前还应检查 GitHub Description、License、README 与公开仓库预期。
