# Linux 部署与 Smoke Test 指南

## 目标

本文档用于在 Linux 服务器上运行 Hermes Agent Software Team MVP 后端，并完成最小端到端验证：创建项目、创建任务、自动推进、执行 Runner、查看状态与事件、验证 Feishu 通知审计。

## 运行前提

- Python 3.12+
- 可执行 `python` / `python3`
- 已安装项目依赖
- 可选：Claude Code CLI 已安装为 `claude`
- 可选：Feishu webhook URL

## 安装依赖

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

## 环境变量

### 必需

无必需环境变量。未设置时服务使用默认 SQLite 路径 `data/app.db`。

### 可选

```bash
export HERMES_DATABASE_PATH=/var/lib/hermes-agent/app.db
export ANTHROPIC_API_KEY=your_claude_code_api_key
export FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook-token
```

说明：

- `HERMES_DATABASE_PATH`：覆盖 SQLite 数据库路径。
- `ANTHROPIC_API_KEY`：Runner execution plan 中以 `${ANTHROPIC_API_KEY}` 占位，不会写入 API 响应、事件或审计记录。
- `FEISHU_WEBHOOK_URL`：仅用于发送 Feishu notification；响应和审计记录不保存 webhook URL。

## 启动服务

开发/单机运行：

```bash
. .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

健康检查：

```bash
curl -s http://127.0.0.1:8000/health
```

期望返回：

```json
{"success":true,"data":{"status":"ok"}}
```

## 最小端到端 Smoke Test

以下命令默认服务运行在 `http://127.0.0.1:8000`。

### 1. 创建项目

```bash
PROJECT_ID=$(curl -s -X POST http://127.0.0.1:8000/api/projects \
  -H 'Content-Type: application/json' \
  -d '{
    "name":"Smoke 自动执行项目",
    "description":"验证自动执行闭环",
    "owner_user_id":"feishu_user_001",
    "repo_url":"https://github.com/example/app",
    "default_branch":"main",
    "initial_requirement":"验证 smoke flow"
  }' | python -c 'import json,sys; print(json.load(sys.stdin)["data"]["id"])')

echo "$PROJECT_ID"
```

### 2. 创建任务

```bash
TASK_ID=$(curl -s -X POST "http://127.0.0.1:8000/api/projects/$PROJECT_ID/tasks" \
  -H 'Content-Type: application/json' \
  -d '{
    "phase":"DEVELOPMENT",
    "owner_agent":"DEV",
    "title":"Smoke Runner Task",
    "description":"echo smoke task",
    "input_artifacts":[],
    "expected_artifacts":["runner_result"],
    "max_retries":3
  }' | python -c 'import json,sys; print(json.load(sys.stdin)["data"]["id"])')

echo "$TASK_ID"
```

### 3. 自动推进一个任务

```bash
RUN_ID=$(curl -s -X POST http://127.0.0.1:8000/api/workers/tick \
  -H 'Content-Type: application/json' \
  -d '{"runner_type":"claude_code_cli","workspace_strategy":"git_worktree"}' \
  | python -c 'import json,sys; print(json.load(sys.stdin)["data"]["tick"]["dispatch"]["task_run_id"])')

echo "$RUN_ID"
```

### 4. 查看 Runner execution plan

```bash
curl -s "http://127.0.0.1:8000/api/runner/task-runs/$RUN_ID/execution-plan"
```

确认返回包含：

- `command`
- `workspace_path`
- `logs_path`
- `stdout_path`
- `stderr_path`
- `diff_path`
- `env.ANTHROPIC_API_KEY` 为 `${ANTHROPIC_API_KEY}` 占位

### 5. 执行 Runner

```bash
curl -s -X POST "http://127.0.0.1:8000/api/runner/task-runs/$RUN_ID/execute"
```

如果本机没有安装或配置 Claude Code CLI，该步骤可能返回 failed，这是预期的运行环境问题。后续可通过 runner 状态和项目事件排查。

### 6. 查看项目状态

```bash
curl -s "http://127.0.0.1:8000/api/projects/$PROJECT_ID/status"
```

### 7. 查看项目事件

```bash
curl -s "http://127.0.0.1:8000/api/projects/$PROJECT_ID/events"
```

应能看到如下一类事件：

- `project_created`
- `task_created`
- `task_started`
- `task_dispatched`
- `automation_tick`
- `worker_tick`
- `task_run_completed` 或 `task_run_failed`

## Feishu 通知审计 Smoke

### 1. 创建 escalation

```bash
ESCALATION_ID=$(curl -s -X POST "http://127.0.0.1:8000/api/projects/$PROJECT_ID/escalations" \
  -H 'Content-Type: application/json' \
  -d '{
    "type":"issue_retry_threshold",
    "phase":"TEST_AND_SECURITY_VALIDATION",
    "source_agent":"PM",
    "target_user_id":"feishu_user_001",
    "retry_count":3,
    "threshold":3,
    "summary":"Smoke escalation 需要用户决策。",
    "options":["continue","manual","cancel"]
  }' | python -c 'import json,sys; print(json.load(sys.stdin)["data"]["id"])')

echo "$ESCALATION_ID"
```

### 2. 查看 notification 审计记录

```bash
curl -s "http://127.0.0.1:8000/api/projects/$PROJECT_ID/feishu-notifications"
```

应看到一条 `pending` notification。

### 3. 发送 notification

```bash
NOTIFICATION_ID=$(curl -s "http://127.0.0.1:8000/api/projects/$PROJECT_ID/feishu-notifications" \
  | python -c 'import json,sys; print(json.load(sys.stdin)["data"][0]["id"])')

curl -s -X POST "http://127.0.0.1:8000/api/feishu/notifications/$NOTIFICATION_ID/send"
```

未配置 `FEISHU_WEBHOOK_URL` 时，notification 会被标记为 `skipped`，原因是 `feishu_webhook_url_not_configured`。

## systemd 示例

```ini
[Unit]
Description=Hermes Agent Software Team API
After=network.target

[Service]
WorkingDirectory=/opt/hermes-agent
Environment=HERMES_DATABASE_PATH=/var/lib/hermes-agent/app.db
Environment=ANTHROPIC_API_KEY=replace-with-real-secret
Environment=FEISHU_WEBHOOK_URL=replace-with-real-webhook
ExecStart=/opt/hermes-agent/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

生产部署时建议通过系统级 secret 管理注入环境变量，不要把真实密钥提交到仓库。

## 验证命令

```bash
.venv/bin/python -m pytest -q
```
