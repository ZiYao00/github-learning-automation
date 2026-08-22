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

如果 refresh 第一次测试遗留的 v0.1 笔记，默认应返回 `legacy_note_refresh_blocked`。确认允许迁移后才使用：

```powershell
python scripts\github_learning.py finalize "<job_dir>" --replace-legacy
```

旧文件原文必须先保存到该 runtime job 的 `legacy_note_backup.md`。
