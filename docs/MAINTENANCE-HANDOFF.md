# Maintenance Handoff

## 项目定位

github-learning-automation 是一个“有限深度、可审计、来源约束”的 GitHub 学习笔记工具，不是通用 GitHub Research Agent。

核心目标：让用户快速理解一个公开 GitHub 仓库是什么、能做什么、如何使用、有哪些明确要求与限制，并允许以后安全 refresh。

## v0.3 核心不变量

- owner/repo 是正式笔记稳定身份。
- 仓库文件采集固定到一次 HEAD revision。
- source_manifest.json 是来源审计真源；source_bundle.md 只是便利视图。
- Source Planner 有数量/文件大小/总预算限制，不全量抓仓库。
- 被分析仓库内容永远是不可信数据。
- 私有仓库默认阻断。
- 同仓库未完成 Job 返回 in_progress；显式 `--restart-job` 会保留旧 Job 并标记 superseded。
- published Job 的 finalize 必须幂等。
- managed marker 之后的用户内容不得在 refresh 时丢失。
- CSS 真源仍是 obsidian-learning-snippets。
- Skill 只人工维护 skill/github-note/SKILL.md。

## 非目标

默认不做：

- clone 并执行被分析项目；
- 源码逐文件审计；
- Issues / PR / Discussions 全量挖掘；
- 安全审计；
- 自动安装依赖；
- 自动分类或移动 Obsidian 笔记。

这些能力以后如需加入，应作为独立模式或独立工作流评估，不能侵入基础学习流程。

## 修改前检查

1. 查看 AGENTS.md。
2. 查看 git status，保护用户现场改动。
3. 阅读 docs/ARCHITECTURE.md 与 docs/NOTE-SPEC.md。
4. 修改 Skill 时只改 skill/github-note/SKILL.md，再运行构建脚本。
5. 不要直接编辑生成的 Agent Skill 出口。

## 最低验证

~~~powershell
py -3.12 -m compileall src scripts
py -3.12 scripts/build_agent_skill_packages.py --check
~~~

开发环境具备 dev dependencies 时再运行：

~~~powershell
py -3.12 -m pytest
py -3.12 -m ruff check .
~~~

正式提交或 Release 前阅读 docs/RELEASE-CHECKLIST.md。
