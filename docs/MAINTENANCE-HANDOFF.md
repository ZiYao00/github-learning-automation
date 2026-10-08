# Maintenance Handoff

## 项目定位

github-learning-automation v0.4 是一个 GitHub Knowledge Capture 工具，不是通用 GitHub Research Agent。

默认产物分三层：

- Research Packet：不可变事实底座；
- Capture Note：Obsidian 人类阅读入口；
- Derived Artifact：以后按需生成的 Deep Note / Compare / Media Brief。

## v0.4 核心不变量

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
- 相同 `packet_id` + 相同 `observation_fingerprint` 返回 `no_change`。
- v0.4 runtime 可恢复；v0.3/v5 或更早活动 Job 不隐式迁移。
- managed marker 之后的用户内容不得在 refresh 时丢失。
- 被分析仓库内容永远是不可信数据。
- 私有仓库默认阻断。
- CSS 真源仍是 `obsidian-learning-snippets`。
- Skill 只人工维护 `skill/github-note/SKILL.md`。

## 三个存储层

- `.runtime/github-learning`：Processing Layer，可恢复 Job 与审计材料；
- `research_root`：Archive Layer，长期保存 Packet / observations；
- `notes_root`：Reading Layer，保存 Capture Note。

不得把三者混为一体。Capture Note 只写逻辑 `packet_id`，不能写 Research Root 绝对路径。

## 非目标

v0.4 默认不做：

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

这些能力以后如需加入，应作为独立模式或 Derived Artifact 评估，不能侵入基础收藏链路。

## 修改前检查

1. 阅读 `AGENTS.md`。
2. 查看工作区改动，保护用户现场。
3. 阅读 `docs/ARCHITECTURE.md`、`docs/RESEARCH-PACKET-SPEC.md`、`docs/NOTE-SPEC.md`。
4. 修改 Skill 时只改 `skill/github-note/SKILL.md` 与必要 metadata，再运行构建脚本。
5. 不直接编辑生成的 Agent Skill 出口。
6. 不擅自安装 dev dependencies。
7. 不自动删除 Packet、runtime 或 staging。

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
