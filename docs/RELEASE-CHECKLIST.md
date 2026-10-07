# Release Checklist

## 代码与版本

- pyproject.toml 与 github_learning.__version__ 一致。
- USER_AGENT 从包版本派生，不再单独手填。
- CHANGELOG 已记录本次版本。
- 无无关文件或本地秘密进入变更。

## 核心回归

至少验证：

- doctor 的 configuration_required / auth_recommended / ready。
- Python、Node/Web、Docker、Agent/Skill、极简仓库五类 Source Planner 行为。
- 所有仓库文件来源固定到同一 revision。
- private_repository_blocked。
- source_manifest.json 与 sources/ 一致。
- Prompt Injection 文本只作为数据。
- in_progress 恢复与 `--restart-job` supersede 语义。
- create / refresh / legacy migration / duplicate note。
- finalize 幂等。
- 我的记录区域 refresh 后保留。

## Agent 与文档

~~~powershell
py -3.12 scripts/build_agent_skill_packages.py --check
~~~

确认 AGENTS、README、ARCHITECTURE、NOTE-SPEC、QUICKSTART 与 Skill 没有互相矛盾。

## 自动验证

~~~powershell
py -3.12 -m compileall src scripts
py -3.12 -m pytest
py -3.12 -m ruff check .
~~~

pytest / ruff 只有在本机已经安装 dev dependencies 时运行；项目脚本不得擅自安装依赖。

## GitHub 发布

Release 属于独立授权动作。只有用户明确要求时才：

- commit；
- push；
- 创建 tag；
- 创建 GitHub Release。

v0.3 第一次正式 Release 前还应检查 GitHub Description、License 与 README 是否符合公开仓库预期。
