# Capture Note Spec

Capture Note 是 github-learning-automation 默认写入 Obsidian 的人类阅读入口。它不是 Research Packet 的副本，也不是完整 Wiki。

## 自然产品解读 V2.2（新生成笔记默认）

对于证据充分的新 Job，Agent 在 `analysis.json` 里填写 `editorial_headline` 和 `editorial_body`。ODS V2.2 经过来源核查的标准文章存于 `docs/ODS-NATURAL-PRODUCT-V2.2-REFERENCE.md`，不依赖忽略追踪的本地 Vault 路径。完整笔记优先直接呈现一篇逻辑自然、具有实际价值的阅读文章，而不是机械拼接“它是什么 / 能做什么 / 适合什么场景”等字段。

- 文章必须讲清项目是什么、最有辨识度的能力、用户能得到的实际价值、适用对象和重要限制。
- **官方亮点优先保留：** 当 README 有清晰的产品级“核心能力 / Highlights / Features”清单时，应在文章前段用简洁条目保留有信息量的官方能力概览，再以少量典型场景解释其中最重要的能力。这两个层级互补：概览回答“覆盖哪些能力”，场景回答“怎么帮助用户”。不得只写个人认为特别的两三个功能而遗漏仓库自己强调的整体价值。
- 不要求每个仓库都列七项：根据固定版本 README 的实际条目数和内容价值自适应；技术库、Skill、知识项目也可以保留作者给出的核心模块、工作流阶段或方法论纲要，而不是套用 ODS 的能力分类。
- 对项目方的**无需云端 / 无订阅 / 本地存储 / 遥测 / 隐私**等自述，必须明确“仓库作者声称”，同时保留官方披露的联网例外、外部 API、关闭方式与功能条件；没有实测不写成已验证的隐私或安全承诺。
- 选最有代表性的 1–3 个场景；缺乏证据时允许少写，不凑数，不声称没做过的实际测试。
- 尊重 software / library / agent-skill / knowledge / generic 各自的内容类型；不强求同一套标题。
- 避免营销化、重复摘要、安装命令清单、未经证实的效果和虚构功能。
- 结构字段（summary / why_save / capabilities / use_cases / knowledge_map / evidence_map）仍是事实审查和后续检索的基础，不能因阅读层改为自然文章而省略。
- 新分析带有 `editorial_body` 字段时，完整发布必须通过正文长度、标题、禁止主动图片嵌入等基础检查。以前没有该字段的已存在 Job，继续使用旧结构渲染；Minimal Note 仍照旧。
- 文章后保留重要来源冲突、Research Packet、仓库链接、采集缺口与用户自有的 `## 我的记录`；不得以写作美化替换数据真源。

## 笔记目录（阅读层）

- 可见待整理目录统一写作 `00-待整理`，旧 `00-Inbox` 仅作为待迁移目录名，不再创建新的英文目录。
- 阅读媒体与来源清单继续放 `_repo-data/<owner>/<repo>/`；在共享 `github-note.css` 的 File Explorer 样式中隐藏此数据根目录，**不删除数据**，不影响 WikiLink 引用。个人 Vault 路径只属于配置，不写死到程序核心。
- `00-待整理` 属于文件夹命名规范；当前正式 Capture Note 仍按既有 owner/repo 稳定身份与发布位置工作，不因目录改名自动迁移正式旧笔记。

## README 首图规则（受控例外）

默认只处理**README 展示顺序中的第一张非徽章正文图片**；不按 Git 文件树或媒体索引的字母顺序选择，也不搜索更多图片。SVG/视频、未知外部域名、超限、不在固定 revision 媒体索引中的文件均不下载，不因为首图失败转而选择第二张。

- 只读取当前 Research Packet 固定 revision 的 README，以及该次快照已索引的媒体 SHA/size。
- 只接受仓库内可解析的 PNG/JPG/GIF/WebP，5 MiB 上限；使用固定 revision 的 GitHub Raw 地址取得**最多一张**，并以 Git blob SHA、大小及文件头进行验证。
- 阅读媒体放在 `<notes_root>/_repo-data/<owner>/<repo>/media/readme-first-<blob-sha12>.<ext>`，通过 Obsidian WikiLink 在笔记中引用；另存 revision 对应的简短来源清单。原始 Research Packet 不变。
- 若首图不适合或下载失败，保留文字笔记，不自动抓取第二张、其他视频/截图或仓库整个媒体目录。无图仓库不配占位图。
- 使用 SHA 稳定命名避免覆盖旧图；不自动删除老版本素材。该功能**不是**未来 v0.5 的全量图片/视频自动下载。
- `first_image_status` 会在成功发布结果中报告保存、无图或无法保存的状态。非必要媒体失败不阻断正文保存。


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

**下方为旧 Job 和无 `editorial_body` 分析的兼容章节顺序，不再是新笔记的默认写法。** 新的自然产品解读优先单篇叙述正文，章节仍按证据和项目类型自适应。

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

同一 Packet + 同一 Observation fingerprint 且现有 Capture Note 已指向它时，可返回 no_change，不调用 Agent，也不重写 managed region。**升级渲染规范不会偷偷绕过 no_change，也不会批量覆盖旧笔记。** 如果未来需要使用已有 Packet 重建旧文章，必须增加显式授权且保留用户尾部内容的单独工作流。

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
