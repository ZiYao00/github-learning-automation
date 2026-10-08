# 配置说明

github-learning-automation v0.4.1 使用 `config/local.json` 保存当前电脑的本机路径。该文件已被 Git 忽略；公开仓库只提交 `config/local.json.example`。

## 推荐拓扑

推荐把“真实存储”和“Obsidian 展示”分开：

~~~text
notes_root       = <repo-root>/notes/github
research_root    = <repo-root>/research/github
runtime_root     = <repo-root>/.runtime/github-learning
vault_root       = Obsidian Vault 根目录
notes_subdir     = GitHub-Note

<vault_root>/<notes_subdir>
        ↓ Junction
<notes_root>
~~~

含义：

- `notes_root`：Capture Note 的物理真源；
- `research_root`：Research Packet 的长期物理真源；
- `.runtime`：临时 Job、恢复与审计材料；
- `vault_root / notes_subdir`：Obsidian 展示入口，不是额外副本。

Research Packet 不建议映射进 Obsidian。

## 首次使用

先运行：

~~~powershell
python scripts\github_learning.py onboarding
~~~

如果没有配置，程序只展示建议默认值，不直接创建或采集：

~~~text
<repo-root>/notes/github
<repo-root>/research/github
~~~

用户接受默认值时执行：

~~~powershell
python scripts\github_learning.py configure --use-defaults
~~~

这个命令会：

1. 创建缺失的项目内目录；
2. 把相对路径写入 `config/local.json`；
3. 保留已经存在的其它本机配置。

然后运行：

~~~powershell
python scripts\github_learning.py doctor
~~~

只有存储配置已确认且 GitHub 认证就绪时才进入正常采集。

## 推荐 local.json

~~~json
{
  "notes_root": "notes/github",
  "research_root": "research/github",
  "vault_root": "D:\\YourObsidianVault",
  "notes_subdir": "GitHub-Note"
}
~~~

相对路径以项目根目录为基准。

## 自定义目录

可以使用项目外目录，但自定义目录必须已经存在：

~~~powershell
python scripts\github_learning.py configure --notes-root "D:\MyGitHubNotes"
python scripts\github_learning.py configure --research-root "D:\GitHub-Research"
~~~

`configure` 是 merge 更新，不会因为修改其中一个路径就删除其它字段。

## 绑定 Obsidian

绑定 Vault 只写入 Vault 元数据：

~~~powershell
python scripts\github_learning.py configure `
  --vault-root "D:\Notes\MyVault" `
  --notes-subdir "GitHub-Note"
~~~

如果 `notes_root` 已经配置，它仍然是物理真源。推荐用户自行把：

~~~text
D:\Notes\MyVault\GitHub-Note
~~~

建立为指向：

~~~text
<repo-root>\notes\github
~~~

的 Windows Junction。

doctor/onboarding 会报告：

- `ok`：Vault 子目录解析到 notes_root；
- `mapping_missing`：Vault 展示目录尚未建立；
- `mapping_mismatch`：现有目录没有指向当前 notes_root；
- `direct_vault`：旧配置仍直接把 Vault 子目录作为真实笔记目录；
- `not_configured`：没有配置 Vault。

映射异常不改变 Research Packet 的存储位置。

## 旧 direct-vault 配置

为了避免升级时突然改变已有笔记物理位置：

- 配置只有 `vault_root / notes_subdir` 时继续 direct-vault；
- `configure --use-defaults` 不会自动增加 `notes_root` 并迁移旧笔记；
- 它只补齐安全的缺失默认项，例如 `research_root`；
- 如果用户以后希望切换到 hybrid，应先人工迁移/核对笔记，再显式配置 `notes_root` 和 Junction。

程序不会自动移动、删除或替换现有 Vault 目录。

## 环境变量

支持：

- `GITHUB_LEARNING_NOTES_ROOT`
- `GITHUB_LEARNING_RESEARCH_ROOT`
- `GITHUB_LEARNING_VAULT_ROOT`
- `GITHUB_LEARNING_NOTES_SUBDIR`

环境变量优先于 `config/local.json`。

## 本机数据边界

以下内容都不应提交：

~~~text
config/local.json
notes/
research/
.runtime/
~~~

Capture Note 中只保存逻辑 `packet_id`，不能写 Research Root 绝对路径，因此换盘符或换电脑时只需要修改本机配置。
