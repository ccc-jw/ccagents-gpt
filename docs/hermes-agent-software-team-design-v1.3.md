# Hermes Agent 软件工程团队系统设计方案 v1.3

## 1. 服务模块总览

后端建议先做成模块化单体，不在 MVP 阶段直接拆成微服务。

原因：

```text
MVP 阶段业务状态复杂，但访问量不会很大；
模块化单体更容易维护事务一致性；
后续可以按模块边界拆成服务。
```

推荐模块：

```text
app/
  core/
  config/
  agents/
  projects/
  tasks/
  workflows/
  reviews/
  artifacts/
  runners/
  feishu/
  escalations/
  messaging/
  security/
  observability/
```

---

## 2. 核心模块职责

### 2.1 Config Module

负责：

```text
读取系统配置
解析模型配置
解析 Agent 配置
解析项目级覆盖配置
隐藏 API Key
校验必要配置项
```

核心组件：

```text
ConfigLoader
ModelConfigResolver
AgentConfigResolver
ProjectConfigResolver
```

关键接口：

```text
resolve_model_config(project_id, agent_name)
resolve_agent_config(project_id, agent_name)
```

---

### 2.2 Agent Module

负责管理所有 Agent 的定义和调用。

```text
PM Agent
PDM Agent
Researcher Agent
ARCH Agent
DEV Agent
TEST Agent
SEC Agent
```

核心组件：

```text
AgentRegistry
AgentExecutor
AgentPromptBuilder
AgentPolicyGuard
```

职责边界：

```text
Agent 不直接改数据库状态；
Agent 生成建议、结论、任务输出；
状态流转由 WorkflowEngine 决定；
任务执行由 Runner 完成。
```

---

### 2.3 Project Module

负责项目生命周期的基础管理。

实体：

```text
Project
ProjectMember
ProjectPhase
ProjectEvent
ProjectRisk
```

能力：

```text
创建项目
查询项目
暂停项目
恢复项目
终止项目
记录项目事件
生成项目状态摘要
```

---

### 2.4 Workflow Module

这是核心模块，负责状态机。

核心组件：

```text
WorkflowEngine
StateTransitionGuard
PhaseGateEvaluator
RetryPolicyEvaluator
```

职责：

```text
判断当前阶段是否可进入下一阶段
处理评审通过/失败
处理测试失败回流
处理验收失败回流
处理异常升级
写入 project_events
```

重要原则：

> Agent 不能自己切换项目阶段，所有阶段变化必须经过 WorkflowEngine。

---

### 2.5 Task Module

负责异步任务管理。

实体：

```text
Task
TaskRun
TaskDependency
TaskAssignment
```

能力：

```text
创建任务
分派任务
启动任务
重试任务
取消任务
查询任务状态
记录任务运行结果
```

任务状态：

```text
pending
assigned
running
waiting_review
blocked
failed
completed
cancelled
```

---

### 2.6 Review Module

负责所有评审。

实体：

```text
Review
ReviewComment
ReviewRound
```

能力：

```text
创建评审
收集各 Agent 意见
判断评审是否通过
生成评审报告
触发打回
触发异常升级
```

评审类型：

```text
requirement_review
design_review
testcase_review
design_change_review
security_review
acceptance_review
```

---

### 2.7 Artifact Module

负责产物管理。

实体：

```text
Artifact
ArtifactVersion
ArtifactRelation
```

能力：

```text
登记产物
版本化产物
查询产物
比较产物版本
关联产物到任务/评审/缺陷
```

产物类型：

```text
prd
design_doc
dev_doc
test_case
test_checklist
security_report
acceptance_report
diff_patch
log_file
```

---

### 2.8 Runner Module

负责封装 Claude Code CLI。

核心组件：

```text
ClaudeCodeRunner
RunnerScheduler
WorkspaceManager
RunnerLogCollector
RunnerResultParser
```

职责：

```text
创建 workspace
生成 task-prompt.md
生成 task-context.json
调用 claude CLI
收集 stdout/stderr
收集 diff
收集产物
回写 task_run
```

---

### 2.9 Feishu Module

负责飞书交互。

核心组件：

```text
FeishuBotServer
FeishuCommandParser
FeishuMessageSender
FeishuApprovalHandler
FeishuCardBuilder
```

能力：

```text
接收用户消息
解析 slash command
发送项目状态
发送异常升级通知
处理用户审批选择
绑定飞书用户和项目
```

---

### 2.10 Escalation Module

负责异常升级。

核心组件：

```text
EscalationManager
EscalationPolicyResolver
EscalationNotifier
```

职责：

```text
检查 retry_count
判断是否超过阈值
暂停自动推进
生成用户决策选项
通过 PM Agent 发送飞书通知
处理用户决策结果
```

---

### 2.11 Messaging Module

负责 Agent 间结构化消息。

实体：

```text
AgentMessage
MessageThread
MessageAttachment
```

职责：

```text
Agent 间问题流转
需求问题发给 PDM
设计问题发给 ARCH
流程问题发给 PM
记录消息状态
禁止违规通信
```

---

## 3. 后端 API 设计草案

### 3.1 项目 API

```http
POST /api/projects
GET /api/projects
GET /api/projects/{project_id}
POST /api/projects/{project_id}/pause
POST /api/projects/{project_id}/resume
POST /api/projects/{project_id}/cancel
GET /api/projects/{project_id}/status
GET /api/projects/{project_id}/events
```

创建项目请求：

```json
{
  "name": "用户登录功能",
  "description": "实现账号密码登录、错误提示和权限校验",
  "owner_user_id": "feishu_user_001",
  "repo_url": "https://github.com/example/app",
  "initial_requirement": "需要实现登录功能"
}
```

---

### 3.2 任务 API

```http
POST /api/projects/{project_id}/tasks
GET /api/projects/{project_id}/tasks
GET /api/tasks/{task_id}
POST /api/tasks/{task_id}/assign
POST /api/tasks/{task_id}/start
POST /api/tasks/{task_id}/cancel
POST /api/tasks/{task_id}/retry
GET /api/tasks/{task_id}/runs
```

创建任务请求：

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
  "max_retries": 3
}
```

---

### 3.3 Workflow API

```http
GET /api/projects/{project_id}/workflow
POST /api/projects/{project_id}/workflow/advance
POST /api/projects/{project_id}/workflow/reject
POST /api/projects/{project_id}/workflow/transition
```

阶段推进请求：

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

注意：

```text
外部不能随便调用 transition；
必须经过 StateTransitionGuard 校验。
```

---

### 3.4 Review API

```http
POST /api/projects/{project_id}/reviews
GET /api/projects/{project_id}/reviews
GET /api/reviews/{review_id}
POST /api/reviews/{review_id}/comments
POST /api/reviews/{review_id}/complete
```

提交评审意见：

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

### 3.5 Artifact API

```http
POST /api/projects/{project_id}/artifacts
GET /api/projects/{project_id}/artifacts
GET /api/artifacts/{artifact_id}
GET /api/artifacts/{artifact_id}/versions
POST /api/artifacts/{artifact_id}/versions
```

登记产物：

```json
{
  "task_id": "task_001",
  "artifact_type": "design_doc",
  "name": "detail-design-final.md",
  "path": "docs/design/detail-design-final.md",
  "version": "v1",
  "created_by": "ARCH"
}
```

---

### 3.6 Runner API

```http
POST /api/runner/task-runs
GET /api/runner/task-runs/{task_run_id}
POST /api/runner/task-runs/{task_run_id}/cancel
GET /api/runner/task-runs/{task_run_id}/logs
```

创建 Runner 执行：

```json
{
  "task_id": "task_001",
  "project_id": "proj_001",
  "agent": "DEV",
  "runner_type": "claude_code_cli",
  "workspace_strategy": "git_worktree"
}
```

---

### 3.7 Escalation API

```http
GET /api/projects/{project_id}/escalations
GET /api/escalations/{escalation_id}
POST /api/escalations/{escalation_id}/decision
```

用户决策请求：

```json
{
  "decision": "continue",
  "comment": "再自动修复一轮"
}
```

---

### 3.8 Feishu Webhook API

```http
POST /api/feishu/events
POST /api/feishu/interactive
```

职责：

```text
/api/feishu/events 接收普通消息、命令、群聊事件
/api/feishu/interactive 接收卡片按钮点击、审批选择
```

---

## 4. Runner 进程模型

推荐采用：

```text
主服务进程
  ↓
任务队列
  ↓
Runner Worker Pool
  ↓
每个 task_run 启动独立子进程
  ↓
claude CLI
```

结构：

```text
Backend API
  |
  v
Task Queue
  |
  v
Runner Worker
  |
  +--> WorkspaceManager.create()
  +--> PromptBuilder.build()
  +--> Claude CLI subprocess
  +--> LogCollector.collect()
  +--> ResultParser.parse()
  +--> ArtifactCollector.collect()
  +--> TaskRunRepository.update()
```

---

## 5. Runner 执行生命周期

```text
CREATED
  ↓
PREPARING_WORKSPACE
  ↓
BUILDING_CONTEXT
  ↓
RUNNING_CLAUDE
  ↓
COLLECTING_RESULTS
  ↓
PARSING_OUTPUT
  ↓
COMPLETED / FAILED / TIMEOUT / CANCELLED
```

---

## 6. Runner 超时与失败处理

建议区分：

```text
claude_cli_failed
command_timeout
workspace_prepare_failed
artifact_collect_failed
result_parse_failed
permission_denied
model_config_invalid
```

失败后：

```text
1. task_run 标记 failed
2. task retry_count + 1
3. WorkflowEngine 判断是否重试
4. EscalationManager 判断是否超过阈值
5. PM Agent 决定是否继续推进或通知用户
```

---

## 7. Runner Workspace 策略

### 7.1 文档类任务

适用：

```text
PDM
Researcher
ARCH 文档输出
PM 报告
```

策略：

```text
copy_workspace
```

特点：

```text
复制必要文件
允许写 docs/
不一定需要完整 git worktree
```

---

### 7.2 代码类任务

适用：

```text
DEV
```

策略：

```text
git_worktree
```

特点：

```text
基于目标分支创建独立 worktree
允许修改代码
执行测试
生成 diff.patch
```

---

### 7.3 测试类任务

适用：

```text
TEST
```

策略：

```text
clean_git_worktree
```

特点：

```text
从 DEV 变更后的分支创建干净环境
只读或有限写入测试报告
运行测试命令
记录结果
```

---

### 7.4 安全类任务

适用：

```text
SEC
```

策略：

```text
readonly_worktree 或 container_readonly_mount
```

特点：

```text
默认不允许修改代码
允许生成 security report
允许运行 SAST / dependency scan
```

---

## 8. 初版数据库 DDL 范围

MVP 第一批表建议只做这些：

```text
projects
project_events
agents
tasks
task_runs
artifacts
reviews
review_comments
issues
escalations
agent_messages
```

不要一开始做太细的权限表、成本表、绩效表。

---

## 9. MVP 推荐技术栈

推荐快速落地技术栈：

```text
语言：Python
Web 框架：FastAPI
数据库：SQLite 起步，后续 Postgres
任务队列：Dramatiq
配置：YAML + 环境变量
Runner：subprocess 调 claude CLI
飞书：官方开放平台 SDK 或直接 HTTP
部署：Linux + systemd / Docker Compose
```

MVP 推荐组合：

```text
FastAPI + SQLite + Dramatiq + Docker Compose
```

原因：

```text
FastAPI 写 API 快
SQLite 降低启动成本
Dramatiq 比 Celery 简洁
Docker Compose 方便部署 Runner Worker
```

---

## 10. 第一阶段目录结构建议

```text
ccagents-gpt/
  app/
    main.py

    core/
      database.py
      config.py
      logging.py

    config/
      config_loader.py
      model_config_resolver.py

    agents/
      registry.py
      base.py
      pm.py
      pdm.py
      dev.py
      test.py

    projects/
      models.py
      schemas.py
      service.py
      router.py

    tasks/
      models.py
      schemas.py
      service.py
      router.py

    workflows/
      state_machine.py
      engine.py
      guards.py

    runners/
      claude_code_runner.py
      workspace_manager.py
      prompt_builder.py
      result_parser.py
      worker.py

    reviews/
      models.py
      service.py
      router.py

    artifacts/
      models.py
      service.py
      router.py

    escalations/
      models.py
      service.py
      router.py

    feishu/
      router.py
      client.py
      parser.py
      card_builder.py

    messaging/
      models.py
      service.py

  docs/
    hermes-agent-software-team-design-v1.2.md
    hermes-agent-software-team-design-v1.3.md

  configs/
    app.yaml

  scripts/
    dev.sh

  tests/
```

---

## 11. 下一步产物

下一步建议产出：

```text
docs/database-ddl-v0.1.md
docs/api-design-v0.1.md
```
