# 飞书接入说明

`yt2feishu` 第一版通过 `feishu-cli` 把生成好的 Markdown 导入为飞书云文档。

## 1. 安装 feishu-cli

`feishu-cli` 官方推荐安装方式：

```bash
curl -fsSL https://raw.githubusercontent.com/riba2534/feishu-cli/main/install.sh | bash
```

Windows 可以去 GitHub Releases 手动下载 `feishu-cli_*_windows-amd64.tar.gz`，解压后把 `feishu-cli.exe` 所在目录加入 PATH。

也可以用 Go 安装：

```bash
go install github.com/riba2534/feishu-cli@latest
```

## 2. 创建并保存飞书应用凭证

```bash
feishu-cli config create-app --save
```

命令会给出授权链接或扫码流程，完成后会把 App ID / App Secret 保存到本机配置。

如果你已经有飞书开放平台应用，也可以用环境变量：

```bash
export FEISHU_APP_ID="cli_xxx"
export FEISHU_APP_SECRET="xxx"
```

## 3. 测试 Markdown 导入

```bash
feishu-cli doc import README.md --title "测试文档" --verbose
```

注意：`doc import` 默认以 Bot 身份建档，文档归属于应用。如果你在飞书里看不到文档，需要给自己的邮箱授权，或在 `feishu-cli` 配置里设置 `owner_email`。

## 4. 用 yt2feishu 上传

```powershell
.venv\Scripts\python.exe -m yt2feishu "https://www.youtube.com/watch?v=VIDEO_ID" --upload --feishu-verbose
```

如果 `feishu-cli.exe` 不在 PATH，可以显式传路径：

```powershell
.venv\Scripts\python.exe -m yt2feishu "https://www.youtube.com/watch?v=VIDEO_ID" --upload --feishu-cli "C:\path\to\feishu-cli.exe"
```

先检查但不真正写入：

```powershell
.venv\Scripts\python.exe -m yt2feishu "https://www.youtube.com/watch?v=VIDEO_ID" --upload --feishu-dry-run
```

## 常见问题

### 报 scope 不足

需要在飞书开放平台给应用开通文档相关权限。`feishu-cli` 的错误信息通常会带缺失 scope。

### 导入成功但自己看不到

这是因为文档由 Bot 创建。可以使用 `feishu-cli perm add <doc_id> --doc-type docx --member-type email --member-id you@example.com --perm full_access` 给自己授权。

### 需要导入到指定文件夹或知识库

第一版先只创建普通飞书文档。后续可以在导入后追加 `drive move` 或 `wiki move-docs`，把文档移动到指定文件夹或知识库。

