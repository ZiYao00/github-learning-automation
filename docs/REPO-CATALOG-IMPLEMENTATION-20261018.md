# Catalog v1 实施与验收记录

本记录对应 `REPO-CATALOG-EXECUTION-HANDOFF-20261018.md` 的已批准方案。功能代码、说明与本地分发包已实施；离线回归和真实文件级验收通过。Obsidian 客户端实点与完整可选开发工具检查仍待验证，不将其表述为全部验收完毕。

## 已实施范围

- Phase 0：核对项目规则、源码、Git、配置、doctor、原收藏清单和笔记类型；在忽略目录 `.runtime/catalog-rollout/` 保存只读基线、原 Markdown 副本与验证脚本。实施开始时历史样式改动已不在未提交清单中，仅有无关 `temp/`，本轮未触碰该内容。
- Phase A：新增 `catalog add/list/nav`，严格五列主表局部更新、逐项规范化和去重、中文简介输入、SHA 冲突保护、派生导航。真实导航已创建，重复执行不重写。
- Phase B：新增 `catalog reconcile` 和正式 CLI 成功后的独立索引后处理。充分研究、Minimal Note、历史缺字段、重复身份、预览、人工暂缓及已实测分别处理；故障与中断可单独同步恢复，不重采或回滚正式笔记。
- Phase C：更新 AGENTS、README、Quickstart、Agent 接入说明及唯一 Skill 真源；既有脚本生成 5 个客户端出口和完整 `release/skill.zip`，包含 6 项资源。Skill 2.4.0、Catalog 契约 1；原 Job v8、编辑契约 2.2、CSS v0.4 不变。

## 代码与文档入口

核心新增 `src/github_learning/catalog.py`、`catalog_nav.py`；命令路由和可选后处理位于 `cli.py`。`lifecycle.py` 仅修改 Skill 版本常量，没有改动正式发布实现。原 `publish_safety.py`、`note_template.py`、`input_resolver.py`、`config.py` 保持不变。

后续 Agent 从 `AGENTS.md` 开始，轻量收藏与同步操作以 `docs/REPO-CATALOG.md` 为准；正式研究继续遵循既有 NOTE-SPEC 与 Research Packet 契约。不要拿旧交接中的“未实施”历史快照重新覆盖当前实现。

## 实际验证

| 检查 | 结果 |
| --- | --- |
| 新增 Catalog 专项 unittest | 53 项通过 |
| 原有可直接运行的标准库回归 | 61 项通过 |
| 合并标准库回归 | 114 项通过 |
| src/scripts/tests Python 语法 | 54 个文件解析通过，使用 Python 3.10 语法目标检查；非全版本运行测试 |
| doctor | ready，无 actions/warnings/issues；版本与分发包一致 |
| 5 个 Skill 出口、6 项资源、实际 ZIP 内容与哈希 | 构建器检查通过 |
| 真实清单重复导入预览 | 34 条全部识别为已存在，不追加 |
| 真实导航内部链接 | 6 个目标均存在于配置的 Vault |
| 真实导航二次生成与 reconcile | no_change，无无谓覆盖 |
| 原收藏清单 | 整个文件字节完全一致，含 34 条收藏与 10 条推荐 |
| 原正式笔记及媒体 | 哈希无变化 |
| Research | 77 个原文件逐项哈希无变化 |
| 本机配置、无关 temp、既有发布与路径核心 | 哈希无变化 |

测试包含真实 Windows 双进程、不同项目根共用笔记目录的竞争写入；真实临时 Junction；使用合成来源驱动实际 v8 prepare/finalize 与 no_change；Minimal Note；模拟索引写入失败、并发编辑和进程中断后的恢复。以上不代表重新访问 GitHub 或重新生成用户正式笔记。

## 当前真实数据结果

34 条收藏仍为 19 条待归档、15 条暂缓；该清单内暂无可勾选的充分研究记录。导航另列 3 篇未加入收藏表但结构有效的正式笔记、2 篇待核验历史笔记；3 篇非正式预览不参与完成判定。没有自动补写历史字段，没有把未列入清单的正式笔记加入收藏。

真实用户目录新增可见文件仅为 `00-GitHub导航.md`；另有 `.github-catalog/.locks/` 的内部持久锁。不要清理活动锁文件。验证材料、备份和运行日志留在项目忽略目录，不进入公共分发。

## 尚未验证与边界

1. 未完成真实 Obsidian Reading / Live Preview 界面的点击和表格渲染验收。文件存在性与编码测试不能替代客户端验收。
2. 本机缺少 pytest/ruff，也不存在本项目 `.venv`。未安装依赖，完整 pytest / ruff 不声称通过。最初直接 unittest 全量发现还包含 pytest 测试及 src 导入路径问题；通过的 114 项是明确选择的可运行标准库测试。
3. 网页端旧 Skill 没有被自动替换；需要使用当前 `release/skill.zip` 更新相应客户端。磁盘生成出口一致不等于所有 Agent 已安装新包。
4. 目录中的人工“暂缓／已实测”优先保留；来源不足或矛盾报告出来，不静默降级。锁和 SHA 检查保护遵循协议的本机流程，但不宣称与外部编辑器存在跨文件原子事务。

## 恢复与复核

```powershell
python scripts/github_learning.py catalog list --summary
python scripts/github_learning.py catalog reconcile --dry-run
python scripts/github_learning.py catalog reconcile
python -B -m unittest discover -s tests -p "test_catalog*.py" -q
python -B scripts/build_agent_skill_packages.py --check
```

索引失败时先检查 `catalog_sync` 与差异，再同步；保留正式发布结果，不重复 prepare、不自动重启 Job 或迁移旧笔记。需要撤销功能时可按具体代码 diff 恢复，但不得删除原收藏、笔记、Research Packet 或运行时审计文件。

本轮未安装依赖、未清理用户文件、未更改共享 CSS、未提交或推送 Git、未创建远端 Release。
