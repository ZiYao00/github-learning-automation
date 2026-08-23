# 快速测试

## 0. 首次运行门禁

```powershell
python scripts\github_learning.py doctor
```

全新环境应明确返回 `configuration_required`，而不是 `ok`；此时 `prepare` 不能创建 runtime job。

配置 Vault：

```powershell
python scripts\github_learning.py configure --vault-root "D:\Notes\MyVault" --notes-subdir "GitHub-Note"
```

再次 `doctor`：

- 已登录 GitHub CLI / 已有 Token → `ready`；
- 未登录 → `auth_recommended`。

未登录时，默认 `prepare` 应停止；只有显式 `--allow-anonymous` 才允许匿名采集。

## 1. 内容回归

推荐依次使用：

1. 标准 ComfyUI 插件；
2. README 较长的大型 ComfyUI 项目；
3. 普通命令行软件；
4. AI Agent / 自动化项目；
5. README 很少的小仓库。

验收重点：30 秒内能否知道“是什么 / 有什么用”，安装命令是否严格来自官方来源，标签是否不过量，资料不足时是否返回 `source_insufficient` 而不是 error。

## 2. Refresh 回归

同一个仓库连续转换两次：

```powershell
python scripts\github_learning.py prepare "https://github.com/owner/repo"
```

第二次默认应刷新同一篇笔记，`finalize` 返回：

```json
{
  "status": "note_ready",
  "publish_action": "refreshed"
}
```

不应自动生成 `repo（2）.md`。

在笔记 `## 我的记录` 下增加一行人工内容，再 refresh；人工内容必须保留。

如果确实需要第二份独立版本，显式使用：

```powershell
python scripts\github_learning.py prepare "https://github.com/owner/repo" --new-note
```

## 3. 同名仓库与旧版保护

分别测试 `ownerA/demo` 与 `ownerB/demo`。正常文件名应类似：

```text
demo.md
demo · ownerB.md
```

再次学习第一次测试遗留的 v0.1 笔记时，`prepare` 应在 GitHub 采集前返回 `legacy_note_refresh_blocked`，且不创建 runtime job。确认允许迁移后才重新执行：

```powershell
python scripts\github_learning.py prepare "https://github.com/owner/demo" --replace-legacy
```

授权后的 `finalize` 必须先把旧文件原文保存到该 runtime job 的 `legacy_note_backup.md`，再覆盖正式笔记。旧 job 仍可兼容 `finalize --replace-legacy`。

## 4. Obsidian 样式

把以下两个文件复制到 `<vault_root>\.obsidian\snippets\`，并在 Obsidian「设置 → 外观 → CSS 代码片段」中同时启用：

- `obsidian/snippets/learning-lab.css`
- `obsidian/snippets/github-note.css`

GitHub 笔记不需要 `video-note.css`。生成 Frontmatter 必须同时包含 `learning-page` 与 `github-note`。
