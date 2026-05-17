# 后端 API 设计 v0.1

## 1. 设计目标

本 API 设计用于支撑 Hermes Agent 软件工程团队平台 MVP。

API 面向三类调用方：

```text
飞书回调
内部 Agent / Workflow 调度
Runner Worker
```

MVP 阶段 API 使用 REST 风格，后续如需 Agent 流式交互可增加 WebSocket 或事件流。

---

## 2. 通用响应格式

成功：

```json
{
  "success": true,
  "data": {},
  "request_id": "req_001"
}
```

失败：

```json
{
  "success": false,
  "error": {
    "code": "PROJECT_NOT_FOUND",
    "message": "项目不存在"
  },
  "request_id": "req_001"
}
```

---

## 3. Project API

### 3.1 创建项目

```http
POST /api/projects
```

请求：

```json
{
  "name": "用户登录功能",
  "description": "实现账号密码登录、错误提示和权限校验",
  "owner_user_id": "feishu_user_001",
  "repo_url": "https://github.com/example/app",
  "default_branch": "main",
  "initial_requirement": "需要实现登录功能"
}
```

响应：

```json
{
  "success": true,
  "data": {
    "id": "proj_001",
    "name": "用户登录功能",
    "status": "active",
    "current_phase": "INIT"
  },
  "request_id": "req_001"
}
```

---

### 3.2 查询项目详情

```http
GET /api/projects/{project_id}
```

响应：

```json
{
  "success": true,
  "data": {
    "id": "proj_001",
    "name": "用户登录功能",
    "description": "实现账号密码登录、错误提示和权限校验",
    "owner_user_id": "feishu_user_001",
    "repo_url": "https://github.com/example/app",
    "status": "active",
    "current_phase": "REQUIREMENT_DISCUSSION",
    "created_at": "2026-05-17T10:00:00+08:00",
    "updated_at": "2026-05-17T10:10:00+08:00"
  },
  "request_id": "req_002"
}
```

---

### 3.3 查询项目状态

```http
GET /api/projects/{project_id}/status
```

响应：

```json
{
  "success": true,
  "data": {
    "project_id": "proj_001",
    "current_phase": "TEST_AND_SECURITY_VALIDATION",
    "status": "active",
    "progress_summary": "DEV 已完成开发，TEST 和 SEC 正在验证。",
    "risks": [],
    "pending_user_actions": []
  },
  "request_id": "req_003"
}
```

---

### 3.4 暂停项目

```http
POST /api/projects/{project_id}/pause
```

请求：

```json
{
  "reason": "等待用户确认设计变更"
}
```

---

### 3.5 恢复项目

```http
POST /api/projects/{project_id}/resume
```

请求：

```json
{
  "reason": "用户已确认继续推进"
}
```

---

### 3.6 终止项目

```http
POST /api/projects/{project_id}/cancel
```

请求：

```json
{
  "reason": "用户决定终止当前需求"
}
```

---

## 4. Task API

### 4.1 创建任务

```http
POST /api/projects/{project_id}/tasks
```

请求：

```json
{
  "phase": "DEVELOPMENT",
  "owner_agent": "DEV",
  "title": "实现登录接口",
  "description": "根据 PRD 和详细设计实现登录接口",
  "input_artifacts": [
    "artifact_prd_final",
    "artifact_detail_design"
  ],
  "expected_artifacts": [
    "self_test_report",
    "source_code_diff"
  ],
  "max_retries": 3,
  "deadline": "2026-05-20T18:00:00+08:00"
}
```

响应：

```json
{
  "success": true,
  "data": {
    "id": "task_001",
    "status": "pending"
  },
  "request_id": "req_004"
}
```

---

### 4.2 查询任务列表

```http
GET /api/projects/{project_id}/tasks
```

可选查询参数：

```text
status
phase
owner_agent
```

---

### 4.3 分派任务

```http
POST /api/tasks/{task_id}/assign
```

请求：

```json
{
  "assigned_to": "DEV"
}
```

---

### 4.4 启动任务

```http
POST /api/tasks/{task_id}/start
```

请求：

```json
{
  "runner_type": "claude_code_cli",
  "workspace_strategy": "git_worktree"
}
```

响应：

```json
{
  "success": true,
  "data": {
    "task_run_id": "run_001",
    "status": "created"
  },
  "request_id": "req_005"
}
```

---

### 4.5 重试任务

```http
POST /api/tasks/{task_id}/retry
```

请求：

```json
{
  "reason": "修复测试失败后重试"
}
```

---

### 4.6 取消任务

```http
POST /api/tasks/{task_id}/cancel
```

请求：

```json
{
  "reason": "项目已暂停"
}
```

---

## 5. Workflow API

### 5.1 查询工作流状态

```http
GET /api/projects/{project_id}/workflow
```

响应：

```json
{
  "success": true,
  "data": {
    "project_id": "proj_001",
    "current_phase": "DESIGN_REVIEW",
    "allowed_transitions": [
      "DESIGN_TESTCASE_APPROVED",
      "DESIGN_TESTCASE_REVISION",
      "PAUSED"
    ]
  },
  "request_id": "req_006"
}
```

---

### 5.2 推进阶段

```http
POST /api/projects/{project_id}/workflow/advance
```

请求：

```json
{
  "from_phase": "REQUIREMENT_REVIEW",
  "to_phase": "REQUIREMENT_APPROVED",
  "reason": "需求评审通过",
  "evidence": [
    "review_001"
  ]
}
```

---

### 5.3 驳回阶段

```http
POST /api/projects/{project_id}/workflow/reject
```

请求：

```json
{
  "from_phase": "DESIGN_REVIEW",
  "to_phase": "DESIGN_TESTCASE_REVISION",
  "reason": "安全评审发现 token 策略缺失",
  "evidence": [
    "review_002"
  ]
}
```

---

## 6. Review API

### 6.1 创建评审

```http
POST /api/projects/{project_id}/reviews
```

请求：

```json
{
  "type": "design_review",
  "phase": "DESIGN_REVIEW",
  "owner_agent": "ARCH",
  "participants": [
    "PM",
    "PDM",
    "DEV",
    "TEST",
    "SEC"
  ],
  "input_artifacts": [
    "artifact_detail_design_draft",
    "artifact_api_design",
    "artifact_db_design"
  ]
}
```

---

### 6.2 提交评审意见

```http
POST /api/reviews/{review_id}/comments
```

请求：

```json
{
  "reviewer_agent": "SEC",
  "status": "fail",
  "severity": "major",
  "comment": "当前设计没有说明 token 过期策略",
  "required_change": "补充 token 过期、刷新和失效策略",
  "related_artifact": "artifact_detail_design_draft"
}
```

---

### 6.3 完成评审

```http
POST /api/reviews/{review_id}/complete
```

请求：

```json
{
  "conclusion": "failed",
  "summary": "设计评审未通过，需要补充 token 策略。"
}
```

---

## 7. Artifact API

### 7.1 登记产物

```http
POST /api/projects/{project_id}/artifacts
```

请求：

```json
{
  "task_id": "task_001",
  "artifact_type": "design_doc",
  "name": "detail-design-final.md",
  "path": "docs/design/detail-design-final.md",
  "version": "v1",
  "created_by": "ARCH",
  "metadata": {
    "phase": "DESIGN_REVIEW"
  }
}
```

---

### 7.2 查询项目产物

```http
GET /api/projects/{project_id}/artifacts
```

可选查询参数：

```text
artifact_type
created_by
status
```

---

## 8. Runner API

### 8.1 创建 Runner 执行

```http
POST /api/runner/task-runs
```

请求：

```json
{
  "task_id": "task_001",
  "project_id": "proj_001",
  "agent": "DEV",
  "runner_type": "claude_code_cli",
  "workspace_strategy": "git_worktree"
}
```

响应：

```json
{
  "success": true,
  "data": {
    "task_run_id": "run_001",
    "status": "created"
  },
  "request_id": "req_007"
}
```

---

### 8.2 查询 Runner 执行

```http
GET /api/runner/task-runs/{task_run_id}
```

响应：

```json
{
  "success": true,
  "data": {
    "id": "run_001",
    "task_id": "task_001",
    "status": "running_claude",
    "workspace_path": "/workspaces/runs/run_001",
    "logs_path": "/logs/run_001.log"
  },
  "request_id": "req_008"
}
```

---

### 8.3 取消 Runner 执行

```http
POST /api/runner/task-runs/{task_run_id}/cancel
```

请求：

```json
{
  "reason": "用户暂停项目"
}
```

---

## 9. Escalation API

### 9.1 查询项目异常升级

```http
GET /api/projects/{project_id}/escalations
```

---

### 9.2 提交用户决策

```http
POST /api/escalations/{escalation_id}/decision
```

请求：

```json
{
  "decision": "continue",
  "comment": "再自动修复一轮"
}
```

支持 decision：

```text
continue
redesign
manual
cancel
change_requirement
```

---

## 10. Feishu Webhook API

### 10.1 接收飞书事件

```http
POST /api/feishu/events
```

处理：

```text
普通消息
slash command
群聊消息
用户 @ Bot
```

---

### 10.2 接收飞书卡片交互

```http
POST /api/feishu/interactive
```

处理：

```text
批准当前阶段
驳回当前阶段
异常升级决策
暂停项目
恢复项目
```

---

## 11. Agent Message API

### 11.1 创建 Agent 消息

```http
POST /api/projects/{project_id}/agent-messages
```

请求：

```json
{
  "from_agent": "DEV",
  "to_agent": "PDM",
  "message_type": "requirement_question",
  "phase": "DEVELOPMENT",
  "title": "登录失败是否需要区分账号不存在和密码错误",
  "content": "PRD 当前只说明登录失败返回错误提示，未明确是否需要区分账号不存在和密码错误。",
  "related_artifacts": [
    "artifact_prd_final"
  ]
}
```

---

### 11.2 查询 Agent 消息

```http
GET /api/projects/{project_id}/agent-messages
```

可选查询参数：

```text
to_agent
from_agent
message_type
status
```

---

## 12. 下一步

API v0.1 完成后，下一步可以进入 FastAPI 项目骨架和数据库模型实现。
