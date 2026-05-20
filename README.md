# AI-PR-Reviewer

这是一个基于 **FastAPI + PyGithub + 大模型 API** 的 GitHub Pull Request 自动审查工具。

当仓库收到 **PR 创建（opened）** 事件时，服务会：

1. 读取该 PR 的代码 Diff
2. 将 Diff 包装到审查 System Prompt（关注 Bug、安全、可读性）
3. 调用大模型生成评审意见
4. 自动把评审意见评论到该 PR 页面

## 1. 安装依赖

```bash
pip install -r requirements.txt
```

## 2. 配置环境变量

请在运行前设置以下变量：

- `GITHUB_TOKEN`：GitHub Personal Access Token（需要对目标仓库有读写 PR 评论权限）
- `OPENAI_API_KEY`：大模型 API Key
- `OPENAI_MODEL`：（可选）默认 `gpt-4o-mini`
- `OPENAI_API_BASE`：（可选）默认 `https://api.openai.com/v1`
- `GITHUB_WEBHOOK_SECRET`：（可选，推荐）用于校验 GitHub Webhook 签名

示例：

```bash
export GITHUB_TOKEN="ghp_xxx"
export OPENAI_API_KEY="sk-xxx"
export OPENAI_MODEL="gpt-4o-mini"
export GITHUB_WEBHOOK_SECRET="your_webhook_secret"
```

## 3. 启动服务

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 4. 配置 GitHub Webhook

在目标仓库中设置：

- **Payload URL**: `http://<your-server>/webhook`
- **Content type**: `application/json`
- **Secret**: 与 `GITHUB_WEBHOOK_SECRET` 保持一致（如果启用）
- **Events**: 选择 `Pull requests`

## 5. 接口说明

### `POST /webhook`

- 接收 GitHub Pull Request Webhook
- 仅处理 `pull_request` 且 `action=opened`
- 成功后会自动在 PR 下发布 `AI Code Review` 评论

### `GET /`

- 健康检查接口，返回：`{"status": "ok"}`
