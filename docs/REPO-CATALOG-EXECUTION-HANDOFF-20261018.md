# GitHub 仓库候选清单、归档状态与 Obsidian 导航：执行审查 / 跨窗口交接

> 审查日期：2026-10-18
> 当前阶段：**只完成设计审查与交接文档；未实施功能、未修改 Vault、未创建导航页、未提交/推送。**
> 执行门禁：新窗口须先核对当前源码 / Git 状态 / Vault 配置；获得用户“方案通过，开始执行”等明确实施授权后，才可以按阶段修改。
> 此文档用于承接项目，不替代 `AGENTS.md`、`docs/NOTE-SPEC.md` 或 `skill/github-note/SKILL.md` 的现有权威规范。

## 1. 任务背景与目标

用户在 B 站、X 和 GitHub 日常看到值得研究的仓库，需要 **随手保存 -> LLM 生成简短中文介绍 -> 后续按需正式研究 -> 自动标记研究完成 -> 从 Obsidian 导航打开正式笔记**。

必须保持两种工作强度：

1. **轻量收藏**：允许批量 URL / 帖文片段 / 截图，经 Agent 提取与核验仓库身份、去重、简述价值，不强制运行 GitHub 采集、下载代码或生成 Research Packet。
2. **正式研究**：由用户选择某仓库，执行既有 `prepare -> 归档 Research Packet -> Agent 来源分析 -> finalize`；只在有可信结果时同步收藏状态与 Obsidian 导航。

用户希望使用时操作尽量少，但不希望“每次打开项目就自动研究所有仓库”。不得为此引入新的 Agent、数据库、Web UI、RAG 或平台爬虫。

### 明确不做

- 不部署、克隆、安装被收藏的第三方仓库；不自动调用 B 站/X 登录态或批量抓取。
- 不重建 GitHub Collector，不修改不可变 Research Packet / Evidence Map / Snapshot / v8 事务语义。
- 不自动迁移 direct-vault 到 hybrid/Junction，不改共有 `obsidian-learning-snippets` CSS。
- 不重写现有 34 条收藏、置顶推荐、正式笔记正文、`## 我的记录`、旧 Job 或 Research Packet。
- 不默认修改全局 Agent 指令、MCP、认证凭据；不自动提交、推送、发布或删除文件。

## 2. 已检查的实际现状（事实）

检查了 `AGENTS.md`、`docs/ARCHITECTURE.md`、`docs/CONFIGURATION.md`、`docs/NOTE-SPEC.md`、`docs/AGENT-INTEGRATION.md`、`docs/V0.5-BACKLOG.md`，及源码：

- `src/github_learning/cli.py`：现有子命令为 `onboarding`、`configure`、`doctor`、`prepare`、`finalize`；没有收藏目录批量管理或导航命令。`prepare` 只接受一个 `repository` 参数；不能把整篇多链接帖子直接传给它。
- `src/github_learning/input_resolver.py`：已有 `resolve_repository`，可将合法 `github.com/owner/repo` 或 `owner/repo` 规范化。它会提取文本中的**第一个** URL，因此批量解析必须在其外层显式逐项处理。
- `src/github_learning/note_template.py`：正式笔记 Frontmatter 的 `repo` 是仓库身份；`find_notes_by_repository` 会递归查找同一 repo。managed marker 保护用户尾部；某些旧笔记缺少新版字段。
- `src/github_learning/lifecycle.py`：`prepare` 有 `in_progress` / `no_change` / `update_available` / 冲突等状态；`finalize` 在 `sufficient` 发布完整笔记，在 `insufficient` 发布 Minimal Note。`note_ready` 包含 `note_path`、`repository`、`analysis_status` 等字段。`no_change` 不直接携带 `analysis_status`，必须再检查实际笔记。
- `src/github_learning/publish_safety.py`：正式发布已有按 repo 的操作系统锁、目标 SHA 检查、原子写入和中断恢复；这些保护**不自动覆盖新的收藏清单文件**。新增清单需要自己的竞争写入保护。
- `src/github_learning/config.py`：运行时 `settings.notes_root` 由环境变量、本机配置、Vault direct 模式或项目默认值决定；环境变量优先。当前本机配置采用已兼容的 direct-vault 模式，不能从公开文档假定路径，更不能将真实 Vault/Research Root 路径写入可跟踪文档。
- 现有 Obsidian 收藏文件为 `<notes_root>/00-仓库收藏清单.md`：**34 条互不重复的候选仓库**，主表 **5 列**（仓库、收藏原因、优先级、状态、正式笔记）；主表**上方还有 10 条重点推荐，分属两张 Markdown 表**；后方为状态说明和维护约定。
- `<notes_root>` 下已经有正式旧/新笔记、`00-待整理/`、`_repo-data/` 和 ODS 样式验收 / V2.2 预览。部分正式笔记**未列入上述 34 条清单**；预览含 `source`/`packet_id` 也不代表正式笔记。
- 当前项目 Git 为 `main`，本地领先远端 6 commits；检查时存在**其他任务的未提交更改**：`docs/MAINTENANCE-HANDOFF.md`、`scripts/apply-ods-v22-reading-layout.py`、`scripts/inspect-ods-vault.py`、`scripts/sync_github_note_editorial_css.py`、`tests/test_core.py`、`src/github_learning/style_sources.py`、`tests/test_style_sources.py`、`temp/`。新窗口必须重新检查，**不能覆盖、清理或提交这些非本任务修改**。
- `docs/V0.5-BACKLOG.md` 当前明确冻结 Web UI、MCP Server、SQLite、RAG、自动整理整个 Vault 等较大能力；本次是薄入口和只读导航，不应以此为由重启整套 v0.5 开发。

## 3. 修正后的架构与真源分工（关键设计）

**修正之前“只有一份唯一真源”的笼统说法**。实际上有两个不同领域的权威数据：

| 数据 | 权威来源 | 谁可以更改 |
| --- | --- | --- |
| 收藏意愿、发现原因、优先级、是否暂缓、个人实测说明 | `00-仓库收藏清单.md`（人工可编辑） | 用户及获授权的轻量收藏流程 |
| 已归档事实、分析是否 sufficient、正式文件实际位置 | 已通过校验的 Capture Note + 既有发布结果 | `github-learning-automation` 正式流程 |
| 导航上的研究完成勾选、关联 WikiLink、计数 | **自动生成的导航视图** | 从以上两类真源推导，可随时重建 |

因此 **不能**仅凭收藏表中有“已归档”就认为文件有效；也不能因为 `finalize` 成功就无条件抹掉“暂缓”或“已实测”这类用户决策。

推荐保留现有五列表格，不迁移 34 条；`状态` 目前兼有意愿/归档进度，是现有结构的兼容折中。实现时：
- `待归档`：默认新收藏状态；
- `暂缓`：**人工意愿**，同步时默认保留，若用户主动从此条开始正式研究，可在成功后改为已归档；
- `待补研究`：建议在阶段 B 增加的状态说明，仅对已取得 Minimal Note 但来源不足的对象；
- `已归档`：正式笔记验证通过且 `analysis_status=sufficient`；
- `已实测`：人工确认的使用成果；不能由模型推断或被同步程序降级。
- 对矛盾状态（如表中已归档但笔记丢失），标记为“待核对/异常”并报告，**不要悄悄降级或伪造新笔记**。

长期如果确实频繁需要“暂缓 + 已归档”并存，再讨论将“人工决策”和“归档进度”拆成两列；**首期不做批量 schema 迁移**。

## 4. 深度审查：必须处理的漏洞与冲突

### P0-1：Markdown 主表与置顶推荐互相干扰

收藏文件有推荐区两张表 + 主收藏表。按 `| [` 开头扫描整个 Markdown，或对全部行盲目做 `split("|")`，会把推荐当收藏，造成重复、错列、丢内容。

**约束**：只解析 `## 收藏列表` 到 `## 状态说明` 之间的五列表格；要求分隔行、列数、唯一仓库身份合法；对其他章节字节级保留。遇到人工作出的未知格式变更，**fail closed + 输出差异**，不得以新模板覆盖整篇原文。

### P0-2：WikiLink 中的 `|` 会破坏 Markdown 表格

在五列表格直接填 `[[00-待整理/codexpro|查看笔记]]` 可能被解析成额外一列。写回表格时须正确转义分隔符（例如 Obsidian 表格里 `[[相对路径\|查看笔记]]`），并以真实 Obsidian Reading/Live Preview 验证；导航采用列表时可用常规 `[[路径|标题]]`。生成时还要安全处理方括号、反斜线、管道符和中文文件名。

### P0-3：成功采集与充分研究不能画等号

- `note_ready + analysis_status=sufficient`：验证目标笔记真实存在、Frontmatter repo/状态/必要 marker 正确后，才标记研究完成。
- `note_ready + analysis_status=insufficient`：只表示 Minimal Note 已保存，**不勾选完整研究**；可提供链接与“待补研究”提示。
- `no_change`：重新读取笔记证实 sufficient 与正式身份；不能仅凭状态码认定完整研究。
- `update_available`、`analysis_required`、`in_progress`、`supplement_selection_required`、冲突或错误：保持当前收藏状态；绝不自动 `--refresh-evidence`、`--restart-job`、`--replace-legacy`。
- `已实测`：只能源于实际测试与人的确认，不能从 README、论文或 Agent 感觉生成。

### P0-4：两个文件不能假装成一个事务

`finalize` 的单仓库锁只保证正式笔记发布。新增清单、导航是另外两个文件；**不存在天然的跨三文件原子提交**。

**约束**：不要为更新清单而改变 `finalize` 的原有 `note_ready` 成功语义；采用“正式发布成功 -> 独立同步索引 -> 导航重建”，同步失败返回**独立可见警告**，保存原本已完成的正式研究结果。必须提供可重复的 `reconcile/sync` 入口，从权威笔记重新计算，解决 `finalize` 后进程中断、电脑断电或同步报错。相同输入重复执行保持幂等。

### P0-5：并发与人工编辑冲突

同一时间可能有 Obsidian 手动修改清单、ChatGPT/Codex 自动收藏和其它 Agent 完成研究。整文件重写可能抹掉人工优先级、推荐排序、文字注释。

**约束**：清单更新使用独立跨进程锁 + 首次读取的 SHA-256/版本检查 + 临时文件原子发布 + 写后校验。若文件在解析/写入之间发生变化，拒绝本次写入并提示重新读取与合并。不要为“看似可恢复的冲突”无审查覆盖或循环重试。同步工具不应持有清单锁再去获取 repo lock（避免反向锁序）。导航可独立重建；若状态落后，下次 reconcile 修复。

### P0-6：路径与非正式笔记的误判

实际 `notes_root` 可能为 direct Vault、项目内物理目录 + Junction、或者被环境变量覆盖。不能用固定盘符拼 WikiLink。根据 `settings.notes_root`、`vault_root`、`notes_subdir` 和 `doctor` 的 mapping 状态生成 **Vault 内相对路径**；mapping mismatch/missing 必须警告且避免发布假链接。移动或重命名正式笔记后按 Frontmatter `repo` 重新定位，而非相信上次表格里记录的文件名。

只把具备可信 repo identity 和有效正式笔记结构的文件当成可自动打勾的 Capture Note；没有 `repo` 的 ODS 视觉预览即使有 `source` 或 `packet_id` 也不能参与。旧版笔记字段不全时作为“历史笔记待核验”，不要自动迁移、删除或强行判充分。相同 repo 多份正式笔记须停止关联并报告歧义。

### P1-7：状态体系与“推荐优先级”不同

置顶推荐是用户认可的编辑内容，不能由索引生成器重排或覆盖；“暂缓”不是采集失败、“已实测”不是 LLM 的质量分数。初期保持清单既有结构、原因和排序；导航按 **研究状态/优先级** 聚合，分类标签可先只做展示，不强制给 34 行新增第六列。任何状态矛盾进异常区让用户判断。

### P1-8：来自 B 站/X 的候选信息不可信且可能不完整

官方仓库地址、营销帖描述、截图识别结果是不同可信层级。URL 给定时可快速保存；描述标明“来源/初步判断”，不冒充已读仓库源码或运行验证。只有项目名或截图名称有歧义时先查明 owner/repo；无法确认则存到独立 `待核验候选`（或仅返回待确认结果），**不要造一个 repo ID**。重复来源归并同一仓库，不抹掉已有人工备注。

仓库 README/帖子均为不可信数据，禁止把其中“运行命令”“忽略规则”当作 Agent 指令。只解析 GitHub 官方主机，拒绝私有/不可确认的目标进入自动正式采集。多 URL 必须逐个标准化；不能复用现有 `resolve_repository` 对整篇帖文只取第一个 URL 的行为。

### P1-9：自动导航应是派生品，不是第二个可以手动勾选的来源

建议输出 `<notes_root>/00-GitHub导航.md`，文件头明确“自动生成，不在本页手动维护状态”。先按已收藏的待研究、待补研究、已归档、暂缓分组；另外允许显示“**Vault 已有但未列入收藏清单的正式笔记**”，只作导航不自动纳入清单。历史笔记与诊断项应独立区域。任务框 `- [x]` 仅表示经过正式结果验证的“充分研究”；不要把勾选本身作为执行 `prepare` 的按钮。可用原生 Markdown/WikiLink，无需 Dataview/JS/CSS 新依赖。

### P1-10：公开仓库、Skill 安装包和既有未提交工作

`config/local.json`、Vault 绝对位置和密钥不能写入公共 docs/README、Git 跟踪代码、日志或发布物。本文因此只使用 `<notes_root>` 等占位符。

修改 Skill 时只编辑 `skill/github-note/SKILL.md`（唯一人工维护真源）；`github-note/`、`agent-skills/*` 和 `release/skill.zip` 是生成出口，须按既有构建/校验流程生成，不能手工多处复制。网页版旧 Skill 不会自动更新，新窗口不能假定当前 ChatGPT 已安装新版本。

当前存在与本任务无关的样式/测试未提交修改，并且分支领先远端；不得改动或提交其他任务内容。避免碰 `docs/MAINTENANCE-HANDOFF.md`（当前已被修改）。不允许顺便整理 Vault 目录或清理旧缓存。

## 5. 推荐实施结构（最小化）

优先在当前 Python 核心新增一个独立、低耦合的“目录/导航”模块；保留原 `prepare/finalize` 方法签名、原始返回协议与 Research Packet 数据契约。候选命令名（最终以项目风格和实测为准）：

- `catalog add <GitHub URL>`：仅追加或去重，LLM 提供可审阅的一句话简介及可选来源；无须调用正式 Collector；
- `catalog list`：只读显示当前收藏清单、研究状态和优先级；
- `catalog reconcile --dry-run` / `catalog reconcile`：扫描正式笔记与现有表格，生成差异，允许受控回写，不能擅自覆盖手动“暂缓/已实测”；
- `catalog nav --dry-run` / `catalog nav`：预览或重建 Obsidian 导航；
- `catalog next` 可视为可选只读快捷入口，**不自动批量研究**。

仅作为 API 草案，不是现有可执行命令。初期建议把“正式发布后的同步”放在**编排/薄适配层**，待验证充分后再考虑调用钩子；避免在现有 `finalize` 核心内部添加可能导致发布变慢或改变结果的索引写入。可先实现手工 `reconcile`，再实现自动调用；每次开始工作也可执行只读 `list/reconcile --dry-run`，不是运行整个采集器。

推荐模块划分（实现前再按源码习惯确定）：
- 输入识别与表格局部读写：`src/github_learning/catalog.py`；
- 归档状态核验与导航生成：`src/github_learning/catalog_nav.py`，也可在小规模时合并为一个文件；
- 入口：`src/github_learning/cli.py` 新子命令；
- 测试：单独 `tests/test_catalog.py`，不得为了本任务大改现有 `tests/test_core.py`。

## 6. 分阶段执行与停止点

### Phase 0 — 基线检查（只读）

1. 打开项目，按 `AGENTS.md` 读取约束，再读本文件及本机 `config/local.json`；仅在内存中解析本机真实路径。
2. 再次确认 Git 状态并记录已有非本任务变更；读取主表、置顶推荐、正式笔记的仓库身份和状态。
3. 核对 `doctor` 返回的 `notes_root` 与 `obsidian_mapping`；若不匹配实际 Vault，**停止写入真实用户数据**，不得自动迁移路径。
4. 建立可还原的测试样本/临时 Vault（项目内可忽略的测试目录或 unittest TemporaryDirectory），勿拿用户 34 条清单做首次破坏性测试。

### Phase A — 纯本地收藏与导航（先完成）

A1. 写**严格的局部 Markdown 解析器**（只操作主表；先有只读检查/格式错误输出）。核对 34 条 repo 唯一、5 列、推荐区未触碰、原文格式保真；输入说明里的 `|`/换行/转义需验证。

A2. 实现 `catalog add/list`：标准化 owner/repo，重复添加不新增行，保留已有人工备注/优先级，支持批量输入的逐个结果；不确定身份不得冒充已核实。

A3. 实现 `catalog nav --dry-run`，先验证 Vault 相对路径、正式笔记/历史笔记/预览排除规则，再实现安全写入新导航文件。初期允许“只读从列表生成导航”，但不能自动研究任何仓库。

**Phase A 验收**：34 条旧记录完全保留；重点推荐 10 条及状态说明原样保留；同仓库重复导入幂等；导航中已存在的正式笔记可跳转；预览、历史笔记不能误打完成勾；没有额外外部调用或依赖。

### Phase B — 与正式研究结果联动（A 验收后）

B1. 单独 `reconcile --dry-run`，依据已验证的官方笔记身份/分析状态输出“将更新什么/哪些需人工核对”；不以列表行文本作为完成证据。

B2. 受控 `reconcile` 同步清单/导航，维护手动编辑优先权、独立锁、SHA/原子写入和幂等；对 `note_ready/sufficient`、`insufficient`、`no_change`、`update_available`、`in_progress`、旧版笔记、重复身份、失效路径设置明确分支。

B3. 添加正式 `finalize` 成功后的**薄层**后处理，结果明确区分 `publish_success` 与 `index_sync_success`；模拟中断 / 失败后靠 B2 的 reconcile 修复。**不改变正式发布核心的退出码与事务语义**。

**Phase B 验收**：充分分析成功后有完成勾和准确链接；Minimal Note 未勾选；`no_change` 验证真实旧笔记；中断/索引同步失败不回滚正式文章也不假称全部同步成功；二次运行结果稳定。

### Phase C — Agent 使用说明与分发（最后）

1. 只在功能有离线回归与小范围验收后，更新 `AGENTS.md` / `README.md` / `docs/QUICKSTART.md` 的必要段落，明确“快速收藏”和“正式研究”分工。
2. 更新唯一 Skill 真源 `skill/github-note/SKILL.md`，再按既有脚本构建生成出口/ZIP，检查 `doctor` 与 Skill `contract.json`；若不需要修改现有正式 Job v8 契约，不要擅自升级 Job/编辑契约。
3. 不自动重新安装网页 Skill，也不假设所有 Agent 已同步；明确引导不同客户端按需更新。
4. 不做 Git commit/push/release，除非用户另行授权。

## 7. 测试矩阵（优先离线）

| 场景 | 期望 |
| --- | --- |
| 34 条原表 + 10 条置顶推荐 | 解析主表唯一；推荐原样不动；无误判 |
| 输入同一个 `owner/repo`、大小写变体、`.git`、`tree/...`、多 URL 帖子 | 规范化、逐个去重；不把整帖当单仓库 |
| 不同 owner 但同名仓库 | 两个独立条目 |
| 只有截图名字、无唯一仓库身份 | 待核验，不造地址 |
| URL/简介含 `|`、中英标点、方括号、Markdown 特殊符号 | 五列稳定，无 HTML/脚本注入、无断列 |
| Obsidian 表格内有显示名称的 WikiLink | `\|` 经过转义，客户端可点击 |
| 正式 `note_ready + sufficient` | 校验存在/身份/marker 后才打勾 |
| `note_ready + insufficient` | 仍待补研究，不能勾选完成 |
| `no_change`，旧笔记实际 sufficient 或 insufficient | 通过元信息分支处理，不能只看 no_change |
| `update_available` / blocked / `analysis_required` | 不冒充成功、不偷偷刷新或迁移 |
| 用户手动设置 `暂缓`/`已实测`/改推荐区 | 自动同步不清空、不降级、不重排 |
| 非清单内的老笔记；ODS 视觉预览；同名多份正式笔记 | 导航隔离呈现/报冲突，不加入重复 |
| 文件改名移动、direct Vault、hybrid Junction、mapping mismatch | 重新定位身份；坏映射警告且不生成假链接 |
| 两 Agent 同时收藏、用户编辑期间同步 | 检测冲突、保留人改动、没有丢行 |
| `finalize` 成功后模拟索引同步失败/断电 | 原笔记保持成功；下一次 reconcile 补齐 |
| 第二次 `add/reconcile/nav` | 幂等，无重复/无无谓覆盖 |
| 原有 v6/v7/v8、Prompt 源证据、首图、用户尾部 | 完整旧回归不退化 |

建议先使用标准库 `unittest`、临时目录及模拟 Job/笔记验证，不访问真实 GitHub，也不写真实 Vault；需要真实端到端验收时，单独列明将修改的用户文件并按阶段授权。验收时可选在真正 Obsidian Reading/Live Preview 中人工检查一次表格、复选框、中文 WikiLink 和相对路径。

## 8. 主要取舍与备选路线

**本轮推荐**：本地 Markdown 目录（人工可编辑）+ 严格解析/增量更新 + 正式笔记元信息判定 + 自动生成 Markdown 导航。

不采用的备选：
- **Obsidian Dataview / Bases 作为唯一状态库**：增加客户端插件/查询行为依赖，其他 Agent 纯文件使用更复杂；以后只把它们当可选显示层。
- **SQLite/RAG**：34 条轻量候选无需数据库，还会与项目当前 v0.5 冻结范围冲突。
- **每次收藏都执行完整 prepare**：增加 Token/API/时间消耗，不适合日常随手收藏。
- **让 LLM 自己编辑整篇目录和勾选导航**：易丢人工内容，无法安全识别 sufficient / Minimal / 冲突。
- **在 finalize 内直接写所有索引作为同一事务**：破坏当前单仓库发布边界；实现成本与风险不必要。

## 9. 实施授权、安全与回滚

- **本交接文档仅记录审查结果，不授权实施。** 下一窗口拿到用户批准后，才执行 Phase A；Phase B、C 在同一用户明确授权范围内可连续推进，但每阶段需按验收停点报告。若出现范围重大变化或不可逆操作，应重新确认。
- 首次修改前读取本机最新 Git 状态和目标文件 SHA，保留已有未提交改动。任何受控更新必须可定位具体 diff；对用户清单采用局部增量修改，禁止覆盖整篇推荐内容。
- 回滚功能代码时，可保留新导航为独立衍生文件并按需重建；**不得自动删除**用户清单、已有正式笔记、Research Packet、运行时或其它任务文件。需要清理或目录删除另行授权，默认回收站且不做永久删除。
- 出现 `index_sync_failed` 时报告“正式笔记成功，索引待同步”，通过再次 reconcile 修复，而不是无条件重新执行 GitHub 正式研究。

## 10. 新窗口接手指令（可原样引用）

> 接手本地项目 `<repo-root>`，目标是为 `github-learning-automation` 增加“轻量 GitHub 收藏 -> 待研究列表 -> 正式研究后完成标记 -> Obsidian 导航”。
>
> 先只读打开 `AGENTS.md`、`docs/REPO-CATALOG-EXECUTION-HANDOFF-20261018.md`、`docs/ARCHITECTURE.md`、`docs/CONFIGURATION.md`、`docs/NOTE-SPEC.md`，核对 Git 状态、现有未提交改动、本机 `config/local.json`、`doctor` 和当前 Vault 清单。
>
> 当前已有 34 条候选和 10 条置顶推荐；保证零丢失。以正式 Capture Note 判断研究完成，Minimal Note 不勾；推荐/暂缓/已实测属于人工决策不可静默覆盖。不要让导航成为第二份状态真源。关注表格中的 WikiLink 管道符、用户并发编辑、旧笔记/预览、direct-vault/Junction 与 `no_change` 等边界。
>
> 在得到我的明确实施批准之后，按 Phase 0 -> A -> B -> C 顺序推进。先做离线解析和导航 dry-run，再测试同步与真实小规模验收；不运行全量仓库研究、不部署第三方、不安装依赖、不碰无关 CSS 改动、不提交/推送/发布。每阶段报告实际测试和遗留问题。

