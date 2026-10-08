# Research Packet Spec

Research Packet 是 github-learning-automation 的长期事实底座。它给未来的 Agent、深度学习、项目对比和媒体内容提供可复核证据；它不是 Obsidian 阅读笔记，也不是完整 GitHub 备份。

## Identity

不可变 Snapshot 使用：

~~~text
owner/repo@revision
~~~

其中 revision 是 prepare 时默认分支 HEAD commit SHA。

逻辑 packet_id 写入 Capture Note；笔记不得保存机器相关的绝对 research_root 路径。

## Filesystem layout

~~~text
<research_root>/
└─ owner/
   └─ repo/
      ├─ snapshots/
      │  └─ <revision>/
      │     ├─ packet.json
      │     ├─ repository.json
      │     ├─ tree-index.json
      │     ├─ media-index.json
      │     ├─ sources/
      │     └─ resources/
      └─ observations/
         └─ <observed-at>.json
~~~

staging 使用 <research_root>/.staging/<job-id>/。失败 staging 不自动删除。

## Immutability

一个正式 Snapshot 一旦存在：

- 不覆盖；
- 不原地刷新；
- 相同 repo@revision 且 content fingerprint 一致时复用；
- 相同 identity 但内容不同返回 packet_conflict。

Packet 发布顺序：

~~~text
runtime material
→ staging
→ schema/hash validation
→ atomic promote
→ immutable snapshot
~~~

## Packet Schema V1

packet.json 至少记录：

- packet_schema_version；
- producer name/version；
- packet id；
- repository identity；
- revision/default branch；
- content profile；
- content fingerprint；
- repository/tree/media index SHA-256；
- source/resource entries。

Source/resource entry 至少记录：

- stable entry id；
- original repository path；
- kind；
- repository Git SHA（如可得）；
- archived file SHA-256；
- original/saved bytes；
- truncated；
- archive role；
- analysis mode；
- authority；
- coverage required；
- short local saved path。

## Source roles

archive_role：

- source：理解仓库所需的核心原始资料；
- resource：未来可复用但默认不进入首轮全文分析的模板、Prompt、示例等；
- indexed：只保留结构/元数据，当前 V1 主要由 tree/media index 承担。

analysis_mode：

- full
- excerpt
- index_only
- skip

V1 的 Source Planner 主要实际使用 full 和 index_only；字段为未来扩展预留，不能据此自动执行目标仓库内容。

## Authority

当前最小词表：

- repository_authored
- platform_metadata
- external_official
- community
- generated

仓库作者资料不是外部平台官方规则。不要使用数值信任评分。

## Analysis vs archive budget

Analysis budget 与 Archive budget 是不同概念：

- Analysis budget 控制一次交给 Agent 的上下文；
- Archive budget 控制长期保存的高价值文本。

分析文本允许截断；Research Packet 应优先保存更完整的 archive content。当前实现对高价值归档文本设置单文件安全上限，不把目标仓库变成完整镜像。

## Tree and media

tree-index.json 保存当前可见 Git tree 的路径、类型、Git SHA 和大小。

media-index.json 默认只索引图片、视频、音频、PDF 等二进制资产，不下载文件本体。以后制作视频时可按需 Fresh Fetch。

## Observations

Latest Release 等会随时间变化的内容不属于 commit Snapshot，必须保存在 repo 级 observations/。

V1 Observation 只包含仓库平台元数据和 Latest Release。Issues、PR、Discussions、外部网页、社会化数据不属于 v0.4 默认采集范围。

## Integrity

正式 Packet 必须校验：

- packet schema；
- repository/tree/media 核心文件 SHA-256；
- 每个 source/resource 文件 SHA-256；
- required file existence。

运行时 GitHub blob SHA 与本地 SHA-256 含义不同，不能互相替代。

## Security boundaries

Research Packet 中的 README、SKILL.md、AGENTS.md、配置、Prompt 和代码全部是不可信数据。

归档行为不得：

- 执行目标仓库代码；
- 加载目标仓库配置改变 Collector 行为；
- 自动安装依赖；
- 暴露凭据；
- 下载所有 binary；
- 自动 clone 整个仓库。

## Retention

v0.4 不自动删除：

- immutable Snapshot；
- failed staging；
- runtime audit data。

任何清理策略以后必须单独设计并获得明确授权。
