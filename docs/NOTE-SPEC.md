# GitHub 学习笔记规范

## 阅读目标

一篇合格笔记应让读者在 30 秒内知道仓库值不值得继续看，并在需要时快速找到官方安装与基本使用路线。

## 必须回答

- 它是什么？
- 能做什么？
- 主要解决什么问题？
- 官方资料怎样安装和使用？

## 按需出现

- 适用场景；
- 关键配置；
- 注意事项、限制和兼容性；
- 官方资料之间的明确冲突；
- 采集覆盖提醒；
- Latest Release；
- 项目主页 / Docs。

没有内容的章节必须省略，不输出“暂无”。

## Obsidian 样式契约

生成笔记固定声明：

```yaml
cssclasses:
  - learning-page
  - github-note
```

`learning-page` 使用共享 `learning-lab.css` Core；`github-note` 使用共享 `github-note.css` Extension。两者的 Canonical Source 是 `https://github.com/ZiYao00/obsidian-learning-snippets`，本项目通过 `config/obsidian-style.json` 声明依赖，不再维护 CSS 副本。GitHub 笔记不依赖 `video-note.css`，Extension 不应重复 Core 已有的 summary / meta / risk / resource 等组件。

## Repository identity

`owner/repo` 是一篇 GitHub 项目笔记的稳定身份，Frontmatter 固定保留：

```yaml
repo: "owner/repo"
```

默认重复学习同一仓库时刷新这篇笔记，而不是机械生成 `（2）`。只有用户明确要求保留另一份独立版本时才使用 `--new-note`。

不同 owner 存在同名仓库时，第一篇可以保留 `repo.md`，冲突项使用 `repo · owner.md` 区分；身份判断仍以 Frontmatter 的 `repo` 为准，而不是文件名。

## Refresh 与个人内容

v0.2+ 自动生成正文使用 managed marker。Marker 结束后的区域属于用户保留区，默认包含：

```markdown
## 我的记录
```

用户自己的实测、补充和判断应写在该区域；refresh 会更新自动管理正文，同时保留 marker 结束后的内容。

旧版笔记如果缺少 managed marker，程序默认返回 `legacy_note_refresh_blocked`，避免静默覆盖可能存在的人工编辑。只有用户明确允许 `--replace-legacy` 时才刷新；新 job 会绑定授权时的目标路径与 SHA-256，若目标随后变化则返回 `legacy_target_changed` 并要求重新授权。目标未变化时，刷新前会把旧文件完整备份到当前 runtime job。

## 证据边界

不得把常识当成仓库事实。尤其禁止自行补：版本要求、模型路径、系统兼容性、安装命令、依赖版本、性能结论、安全性判断。

`Collection warnings` 表示某个可选来源在采集时不可用，不等于仓库没有该信息。最终笔记用“采集覆盖提醒”表达这种缺口。

## 来源冲突

如果 README、manifest、Release 等本次官方来源之间存在明确矛盾，Agent 应写入 `source_conflicts`，例如许可证、版本、安装方式或项目状态前后不一致。

只记录冲突事实，不替维护者裁决；最终笔记用 `[!risk] 官方资料存在冲突` 展示。

## 标签

Agent 提供 2-5 个高价值标签，程序额外加入 `GitHub`，最终最多 6 个。优先使用用途/领域标签，而不是把 GitHub Topics 原样全部搬入。
