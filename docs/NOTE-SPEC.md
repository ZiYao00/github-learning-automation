# Capture Note Spec

Capture Note 是 github-learning-automation 默认写入 Obsidian 的人类阅读入口。它不是 Research Packet 的副本，也不是完整 Wiki。

## Product goal

Capture Note 同时满足两个目标：

1. 30 秒内知道这个仓库是什么、为什么值得保存、是否值得继续研究；
2. 以后回来时能看见仓库的知识/项目地图，并能通过 packet_id 回到长期原始证据。

默认不追求把所有教程全文重写进一篇 Markdown。

## Audience

优先给人阅读。

机器可依赖稳定 Frontmatter 和结构字段进行导航，但需要事实时应回到 Research Packet。

## Frontmatter contract

v0.4.x managed note 至少支持：

~~~yaml
repo: "owner/repo"
source: "https://github.com/owner/repo"
updated: "YYYY-MM-DD"
revision: "<commit-sha>"
packet_id: "owner/repo@revision"
content_profile: "software"
capture_status: "saved"
analysis_status: "sufficient"
observation_fingerprint: "<sha256>"
tags:
  - GitHub
cssclasses:
  - learning-page
  - github-note
~~~

不要写绝对 Research Root 路径。

## Full Capture Note

章节继续采用“有内容才出现”：

~~~text
标题 / 仓库元信息
→ 先看结论
→ 为什么值得保存
→ 它是什么
→ 能做什么
→ 适合什么场景
→ 内容地图 / 项目地图
→ 运行要求 / 兼容性 / 部署方式 / 核心结构 / 项目状态（按需）
→ 如何使用
→ 可复用资源
→ 仓库资料冲突
→ 注意事项
→ 深入研究入口
→ 仓库资料
→ 采集覆盖提醒
→ 我的记录
~~~

## Adaptive map

content_profile 决定地图强调什么：

- software：组件、架构、部署、主要工作流；
- library：核心概念、API、示例；
- agent-skill：任务阶段、Workflow、references；
- knowledge：章节、方法论、步骤；
- generic：只根据证据自适应。

地图必须是“看得见仓库里有什么”，不能只写“它包含若干教程”。

## why_save

why_save 回答：

> 未来为什么值得回来研究这个仓库？

它不能只是重复 summary。

## Resource index

resources 是长期归档但默认不进入首轮全文分析的模板、Prompt、示例等。

Capture Note 只给轻量索引：

- 名称；
- 用途（有证据时）；
- 原 repository path。

不能为了填满索引猜测资源用途。

## Evidence Map

source_manifest 中 coverage_required=true 的 source 必须在 analysis.evidence_map 中：

- represented：给出一个或多个 Capture Note target；
- omitted_with_reason：明确说明为什么不进入笔记。

“Agent 已阅读”不等于覆盖。

Evidence Map 是机器质量门禁；coverage_review 继续作为最后语义复核。

## Minimal Capture Note

source_status=insufficient 不再等于收藏失败。

只要 GitHub collection 和 Research Packet 成功，就发布 Minimal Capture Note：

- capture_status=saved；
- analysis_status=insufficient；
- 明确“待进一步研究”；
- 仓库基本信息；
- 已发现 source/resource；
- 当前不足；
- packet_id/revision；
- 仓库链接；
- 我的记录。

Minimal Note 不得伪装成完整分析。

## Source wording

Capture Note 应区分：

- 仓库作者资料；
- GitHub 平台元数据；
- 外部平台官方资料；
- 社区资料；
- 生成内容。

“仓库资料”不等于“外部平台官方规则”。

## Refresh and no-op

owner/repo 仍是笔记稳定身份。

同一 Packet + 同一 Observation fingerprint 且现有 Capture Note 已指向它时，可返回 no_change，不调用 Agent，也不重写 managed region。

不同 revision 生成新 immutable Packet，然后 refresh 同一 Capture Note。

## User-owned tail

managed end marker 后是用户区域，默认：

~~~markdown
## 我的记录
~~~

refresh 不得删除或重写该区域。

Legacy note、duplicate note 和 replace-legacy 的安全边界继续沿用。

## What does not belong here

Capture Note 默认不承担：

- 全部原文保存；
- 完整源码；
- 全部模板正文；
- 深度教程；
- 对外视频脚本；
- 事实数据库。

这些分别属于 Research Packet 或 Derived Artifact。
