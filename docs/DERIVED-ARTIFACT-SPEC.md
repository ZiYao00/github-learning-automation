# Derived Artifact Spec

Derived Artifact 是从已经保存的 GitHub 知识资产继续生成的按需产物。v0.4 只定义输入契约和边界，不实现完整视频生成器。

## Supported artifact classes

V1 只定义三个逻辑类型：

- Deep Note：面向深入学习的长文；
- Compare：多个仓库按统一维度对比；
- Media Brief：给项目介绍文章、短视频、长视频脚本提供事实与编辑输入。

## Source hierarchy

Derived Artifact 的事实来源顺序：

~~~text
Research Packet
+ optional Fresh Observation
+ Capture Note editorial context
→ Derived Artifact
~~~

Research Packet 是事实底座。

Capture Note 只提供：

- 为什么值得保存；
- 用户视角的重点；
- 内容/项目地图；
- 资源入口。

禁止把 Capture Note 当作唯一事实源继续摘要。

## Collector ownership

Derived Artifact 不允许重新实现第二套 GitHub Collector。

需要历史资料时读取 Research Packet；需要当前状态时执行 Fresh Check / Observation。只有用户明确要把新 revision 重新收藏时，才创建新的正式 Research Packet Snapshot。

## Freshness

私人学习和历史回顾可以只使用 archived Packet。

对外发布的文章、视频、演示默认应执行 Fresh Check，至少确认：

- 当前默认分支 HEAD；
- 当前 Latest Release；
- 被脚本依赖的高价值事实是否发生变化。

未来 Media Brief 应记录：

- based_on_packet；
- freshness_checked_at；
- current_revision；
- observations used。

## content_profile routing

不同仓库不使用同一叙事模板：

| content_profile | 推荐派生叙事 |
| --- | --- |
| software | 问题 → 能力 → 架构/部署 → 使用 → 限制 |
| library | 用途 → 核心概念/API → 示例 → 兼容与限制 |
| agent-skill | 任务 → Workflow → references/resources → 输出 |
| knowledge | 问题 → 方法论 → 阶段/章节 → 实践 |
| generic | 只根据已证实内容自适应 |

## Media Brief boundary

v0.4 不生成：

- 成片；
- Storyboard；
- 自动下载图片/视频；
- TTS；
- 剪辑工程。

Media Brief 未来只负责把事实证据和叙事重点交给下游视频工作流。

## Non-goals

Derived Artifact 层不得把主收藏流程变成：

- 全量 GitHub Research Agent；
- RAG 服务；
- Web UI；
- MCP Server；
- 自动 Issues/PR/Discussions 挖掘；
- 目标仓库代码执行环境。
