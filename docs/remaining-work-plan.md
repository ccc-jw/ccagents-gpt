# 剩余工作执行计划

## 目标

把当前后端 MVP 从“可通过 API 手动推进”补齐到“可在本地自动执行、自动通知、可部署运行”的闭环。

## 当前基线

已完成能力：

- Project / Task / Agent / Review / Workflow / Escalation / Issue / Artifact / Agent Message / Runner API。
- Review gate evaluation 与 workflow 阶段推进。
- Project event timeline 与项目状态聚合。
- Feishu inbound command、interactive escalation decision、notification payload、webhook send endpoint。
- Task 批量 dispatch、单任务 dispatch-next。
- Runner execution-plan。
- Automation tick：单步调度 pending task 并返回 execution plan。

最新全量测试：`114 passed`。

## 执行原则

- 继续使用 TDD：先写失败测试，再实现最小代码。
- 每个阶段完成后运行目标测试、相关回归、全量回归。
- 每个阶段单独提交并推送。
- 不真实调用外部服务，除非测试中 mock。
- 不写入 API key 或 webhook secret 到日志、事件或响应。

## 阶段 1：真实 Runner 执行器 MVP

### 目标

新增本地 Runner executor API，能根据已有 execution plan 执行命令、采集输出路径、按退出码回写 task_run 状态。

### 范围

新增：

- `app/runners/executor.py`
- `POST /api/runner/task-runs/{task_run_id}/execute`

测试：

- 成功命令将 task_run 标记为 `completed`。
- 失败命令将 task_run 标记为 `failed`。
- stdout/stderr/log 路径被写入 task_run。
- 不返回或记录环境变量中的密钥。

### 暂不做

- 不直接执行真实 Claude Code CLI 的长任务。
- 不做后台异步进程管理。
- 不做取消正在运行的 OS process。

### 验证

```bash
.venv/bin/python -m pytest tests/test_runner_api.py -q
.venv/bin/python -m pytest -q
```

## 阶段 2：后台 Worker / Scheduler MVP

### 目标

新增本地可调用的 worker tick，封装项目扫描与自动推进：找到 active project，调用 automation tick，返回本轮动作。

### 范围

新增：

- `app/workers/service.py`
- `app/workers/router.py`
- `POST /api/workers/tick`

测试：

- 有 active project 和 pending task 时，自动 dispatch 一个 task。
- 无 pending task 时返回 idle。
- paused/cancelled project 不会调度。
- 记录 `worker_tick` project event。

### 暂不做

- 不实现常驻 while 循环。
- 不在测试中 sleep 或启动真实后台进程。
- 不自动执行 Claude CLI。

### 验证

```bash
.venv/bin/python -m pytest tests/test_workers_api.py -q
.venv/bin/python -m pytest -q
```

## 阶段 3：Feishu 通知触发与审计 MVP

### 目标

把现有 Feishu notification send 能力接入关键事件，同时记录发送审计，避免“发没发、为什么失败”不可见。

### 范围

新增：

- `feishu_notifications` 或等价发送审计表。
- escalation 创建后可触发 notification send。
- runner failed / review gate failed 可生成待发送通知记录。

测试：

- escalation 创建后生成 notification 记录。
- webhook 未配置时记录 `skipped`，原因是 `feishu_webhook_url_not_configured`。
- webhook 配置时 mock httpx，记录 `sent` 和 HTTP status。
- 响应、事件、审计记录不包含 webhook secret。

### 暂不做

- 不做真实飞书生产 API 联调。
- 不做复杂重试队列。

### 验证

```bash
.venv/bin/python -m pytest tests/test_feishu_api.py tests/test_escalations_api.py -q
.venv/bin/python -m pytest -q
```

## 阶段 4：部署与 smoke 收尾

### 目标

补齐 Linux 运行说明与端到端 smoke，保证服务能被部署和手工验收。

### 范围

新增：

- Linux 环境变量说明。
- 服务启动命令。
- 本地 SQLite 路径说明。
- Claude Code CLI / Feishu webhook 配置说明。
- Smoke test 流程：创建 project、创建 task、automation tick、runner execute、查看 status/events。

验证：

```bash
.venv/bin/python -m pytest -q
```

## 完成标准

- 所有阶段实现、测试、提交、推送完成。
- 全量测试通过。
- 文档说明如何在 Linux 上运行最小闭环。
- 仍不泄露任何密钥或 webhook URL。
