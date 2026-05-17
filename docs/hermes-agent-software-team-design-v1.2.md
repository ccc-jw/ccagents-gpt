# Hermes Agent 多 Agent 软件工程团队系统设计方案 v1.2

## 1. 背景与目标

当前核心痛点是：Claude Code CLI 很适合完成单次代码、文档、调研、测试任务，但不擅长长期、异步、多阶段、多角色的软件工程项目管理。

本系统目标是把 Claude Code CLI 作为可被调度的执行引擎，由 Hermes Agent 负责长期项目的编排、记忆、状态和协作。

最终目标：

```text
用户只通过飞书与 PM Agent 交互；
PM Agent 基于 Hermes Agent 协调多个专业 Agent；
Hermes Agent 负责记忆、状态、任务路由、项目生命周期；
Claude Code CLI Runner 负责代码、文档、测试、安全审查等具体执行。
```

---

## 2. 当前已确认核心决策

```text
主架构：Hermes Agent
用户入口：飞书
用户唯一交互角色：PM Agent
执行工具：Claude Code CLI Runner
长期状态：数据库 + 状态机 + Hermes 记忆
任务执行隔离：workspace / git worktree / 容器
模型配置：默认配置 + Agent 覆盖 + 项目覆盖
异常升级：超过默认 3 次，PM 飞书通知用户
```

---

## 3. 总体架构

```text
用户
 ↓
飞书 Bot
 ↓
PM Agent
 ↓
Hermes Agent Orchestrator
 ↓
任务队列 + 状态机 + 数据库 + 记忆系统
 ↓
Claude Code CLI Runner
 ↓
隔离 Workspace / Git Worktree / 容器
 ↓
代码 / 文档 / 测试结果 / 安全报告 / 日志
```

核心组件：

| 组件 | 职责 |
|---|---|
| 飞书 Bot | 用户入口、通知、审批、状态查询 |
| PM Agent | 项目经理，唯一与用户直接交互的 Agent |
| Hermes Agent | 多 Agent 编排、记忆、任务路由、状态管理 |
| Agent Registry | 管理 PM、PDM、ARCH、DEV、TEST、SEC 等角色 |
| State Machine | 控制项目生命周期流转 |
| Task Queue | 异步任务队列 |
| Database | 保存项目、任务、评审、缺陷、产物、事件 |
| ClaudeCodeRunner | 封装 Claude Code CLI 调用 |
| Workspace Manager | 管理 worktree、容器、临时目录 |
| Artifact Store | 保存 PRD、设计文档、测试清单、报告 |
| Escalation Manager | 统一异常升级和飞书通知 |
| ModelConfigResolver | 统一解析每个 Agent 的模型配置 |

---

## 4. Agent 角色设计

### 4.1 PM Agent

职责：

- 接收用户飞书消息
- 创建项目
- 解释用户需求
- 调度 PDM、ARCH、DEV、TEST、SEC
- 监控项目状态
- 检查阶段是否超时
- 处理异常升级
- 汇总风险并通知用户
- 推动项目进入下一阶段

PM Agent 是唯一允许主动联系用户的 Agent。

### 4.2 PDM Agent

职责：

- 与 PM 配合澄清需求
- 生成 PRD
- 修订 PRD
- 维护需求 FAQ
- 处理 ARCH、DEV、TEST、SEC 的需求疑问
- 主导需求评审
- 负责产品验收
- 生成验收报告

产物：

```text
docs/requirements/prd-draft.md
docs/requirements/prd-final.md
docs/requirements/requirement-faq.md
docs/acceptance/acceptance-report.md
```

### 4.3 Researcher Agent

职责：

- 技术调研
- 竞品调研
- 业务流程分析
- 代码现状分析
- 可行性分析

产物：

```text
docs/research/technical-research.md
docs/research/competitor-analysis.md
docs/research/feasibility-report.md
```

### 4.4 ARCH Agent

职责：

- 输出详细设计
- 输出接口设计
- 输出数据库设计
- 技术方案选型
- 风险分析
- 设计评审

产物：

```text
docs/design/detail-design-draft.md
docs/design/detail-design-final.md
docs/design/api-design.md
docs/design/db-design.md
docs/design/technical-risk.md
```

### 4.5 DEV Agent

职责：

- 根据 PRD 和详细设计编码
- 读写代码
- 读写开发相关设计文档
- 写单元测试
- 自测
- 冒烟测试
- 修复测试缺陷
- 修复安全缺陷
- 生成开发自测报告

权限原则：

```text
DEV 可读写代码和开发相关设计文档；
DEV 可读正式详细设计文档；
DEV 如需修改正式详细设计文档，必须提交设计变更；
设计变更由 ARCH/PM 组织评审后合入。
```

产物：

```text
source code
docs/dev/dev-design-notes.md
docs/dev/implementation-notes.md
docs/dev/self-test-report.md
docs/dev/smoke-test-report.md
docs/dev/fix-report.md
```

### 4.6 TEST Agent

职责：

- 根据 PRD 独立设计测试用例
- 生成测试清单 Excel
- 执行测试
- 记录缺陷
- 验证修复结果

产物：

```text
docs/test/test-cases.md
docs/test/test-checklist.xlsx
docs/test/test-report.md
docs/test/defect-report.md
```

### 4.7 SEC Agent

职责：

- 代码安全审查
- 依赖风险分析
- 敏感信息检查
- 权限绕过检查
- 注入风险检查
- 生成安全报告

产物：

```text
docs/security/security-review.md
docs/security/vulnerability-report.md
docs/security/security-validation-report.md
```

---

## 5. 文档 ownership 设计

### 5.1 文档目录建议

```text
docs/
  requirements/
    prd-draft.md
    prd-final.md
    requirement-faq.md
    requirement-review.md

  research/
    technical-research.md
    feasibility-report.md

  design/
    detail-design-draft.md
    detail-design-final.md
    api-design.md
    db-design.md
    design-review.md
    design-change-requests.md

  dev/
    dev-design-notes.md
    implementation-notes.md
    self-test-report.md
    smoke-test-report.md
    fix-report.md

  test/
    test-cases.md
    test-checklist.xlsx
    test-review.md
    test-report.md
    defect-report.md

  security/
    security-review.md
    vulnerability-report.md
    security-validation-report.md

  acceptance/
    acceptance-report.md
    acceptance-issues.md

  project/
    progress-report.md
    risk-report.md
    retrospective.md
```

### 5.2 文档 ownership 矩阵

| 文档 | Owner | 可读 | 可写 | 变更规则 |
|---|---|---|---|---|
| `prd-draft.md` | PDM | 全部 Agent | PDM | 需求评审前可多轮修改 |
| `prd-final.md` | PDM | 全部 Agent | PDM | 评审通过后修改需走需求变更 |
| `requirement-faq.md` | PDM | 全部 Agent | PDM | 回答各 Agent 需求疑问 |
| `technical-research.md` | Researcher | 全部 Agent | Researcher | 调研产物 |
| `detail-design-draft.md` | ARCH | 全部 Agent | ARCH / DEV | 评审前 ARCH 主导，DEV 可补充实现细节 |
| `detail-design-final.md` | ARCH | 全部 Agent | ARCH | 正式设计事实源 |
| `api-design.md` | ARCH | 全部 Agent | ARCH | 接口事实源 |
| `db-design.md` | ARCH | 全部 Agent | ARCH | 数据库设计事实源 |
| `design-change-requests.md` | ARCH | 全部 Agent | ARCH / DEV | DEV 可提交设计变更 |
| `dev-design-notes.md` | DEV | ARCH / DEV / PM | DEV | 开发实现设计沉淀 |
| `implementation-notes.md` | DEV | 全部 Agent | DEV | 实现说明 |
| `self-test-report.md` | DEV | 全部 Agent | DEV | 自测报告 |
| `smoke-test-report.md` | DEV | 全部 Agent | DEV | 冒烟报告 |
| `test-cases.md` | TEST | 全部 Agent | TEST | 测试用例事实源 |
| `test-checklist.xlsx` | TEST | 全部 Agent | TEST | 测试执行清单 |
| `defect-report.md` | TEST | 全部 Agent | TEST | 测试缺陷记录 |
| `security-review.md` | SEC | PM / ARCH / DEV / PDM | SEC | 安全审查 |
| `vulnerability-report.md` | SEC | PM / ARCH / DEV | SEC | 漏洞报告 |
| `acceptance-report.md` | PDM | 全部 Agent | PDM | 产品验收 |
| `progress-report.md` | PM | 用户 / 全部 Agent | PM | 项目进度 |
| `risk-report.md` | PM | 用户 / 全部 Agent | PM | 项目风险 |
| `retrospective.md` | PM | 用户 / 全部 Agent | PM | 项目复盘 |

---

## 6. 权限矩阵

| Agent | 代码 | 需求文档 | 正式设计文档 | 开发设计文档 | 测试文档 | 安全文档 | 飞书用户交互 |
|---|---|---|---|---|---|---|---|
| PM | 不直接改 | 读 | 读 | 读 | 读 | 读 | 是 |
| PDM | 只读 | 读写 | 读 | 读 | 读 | 读 | 否，经 PM |
| Researcher | 只读 | 读 | 读 | 读 | 读 | 读 | 否 |
| ARCH | 只读 | 读 | 读写 | 读 | 读 | 读 | 否 |
| DEV | 读写 | 读 | 读；变更需评审 | 读写 | 读 | 读 | 否 |
| TEST | 只读 | 读 | 读 | 读 | 读写 | 读 | 否 |
| SEC | 只读 | 读 | 读 | 读 | 读 | 读写 | 否 |

---

## 7. 项目生命周期状态机

### 7.1 主状态

```text
INIT
REQUIREMENT_DISCUSSION
PRD_DRAFTING
REQUIREMENT_REVIEW
REQUIREMENT_REVISION
REQUIREMENT_APPROVED
DESIGN_AND_TESTCASE_DRAFTING
DESIGN_REVIEW
TESTCASE_REVIEW
DESIGN_TESTCASE_REVISION
DESIGN_TESTCASE_APPROVED
DEVELOPMENT
DEV_SELF_TEST
TEST_AND_SECURITY_VALIDATION
BUG_FIXING
PRODUCT_ACCEPTANCE
ACCEPTANCE_FIXING
DONE
PAUSED
FAILED
CANCELLED
```

### 7.2 主流程

```text
INIT
 ↓
REQUIREMENT_DISCUSSION
 ↓
PRD_DRAFTING
 ↓
REQUIREMENT_REVIEW
 ↓
REQUIREMENT_APPROVED
 ↓
DESIGN_AND_TESTCASE_DRAFTING
 ↓
DESIGN_REVIEW
 ↓
TESTCASE_REVIEW
 ↓
DESIGN_TESTCASE_APPROVED
 ↓
DEVELOPMENT
 ↓
DEV_SELF_TEST
 ↓
TEST_AND_SECURITY_VALIDATION
 ↓
PRODUCT_ACCEPTANCE
 ↓
DONE
```

### 7.3 失败回流

```text
REQUIREMENT_REVIEW fail
  -> REQUIREMENT_REVISION -> PRD_DRAFTING

DESIGN_REVIEW fail
  -> DESIGN_TESTCASE_REVISION -> DESIGN_AND_TESTCASE_DRAFTING

TESTCASE_REVIEW fail
  -> DESIGN_TESTCASE_REVISION -> DESIGN_AND_TESTCASE_DRAFTING

DEV_SELF_TEST fail
  -> DEVELOPMENT

TEST_AND_SECURITY_VALIDATION fail
  -> BUG_FIXING -> DEV_SELF_TEST

PRODUCT_ACCEPTANCE fail
  -> ACCEPTANCE_FIXING -> BUG_FIXING
```

---

## 8. 阶段门禁设计

### 8.1 需求评审门禁

输入：

```text
prd-draft.md
requirement-faq.md
```

参与角色：

```text
PM
PDM
ARCH
DEV
TEST
SEC
```

通过条件：

```text
所有角色无阻塞问题
PRD 范围清晰
验收标准明确
无明显技术不可行点
无明显安全不可接受风险
```

不通过则打回 PDM。

### 8.2 详细设计评审门禁

输入：

```text
prd-final.md
detail-design-draft.md
api-design.md
db-design.md
```

参与角色：

```text
PM
PDM
ARCH
DEV
TEST
SEC
```

通过条件：

```text
设计覆盖 PRD
接口边界清晰
数据库变更清晰
风险有处理方案
测试和安全可以基于设计开展验证
```

不通过则打回 ARCH。

### 8.3 测试用例评审门禁

输入：

```text
prd-final.md
test-cases.md
test-checklist.xlsx
```

参与角色：

```text
PM
PDM
ARCH
DEV
TEST
SEC
```

通过条件：

```text
覆盖核心业务路径
覆盖异常路径
覆盖边界条件
覆盖回归风险
覆盖安全相关验证点
```

不通过则打回 TEST。

### 8.4 开发自测门禁

输入：

```text
source code
unit test result
self-test-report.md
smoke-test-report.md
```

通过条件：

```text
代码实现完成
单元测试通过
自测通过
冒烟测试通过
无明显阻塞缺陷
```

不通过则 DEV 继续修复。

### 8.5 测试与安全验证门禁

输入：

```text
test-checklist.xlsx
test-report.md
security-review.md
vulnerability-report.md
```

通过条件：

```text
测试清单全部通过
安全问题全部关闭
阻塞缺陷为 0
严重缺陷为 0
中低风险问题有明确处理结论
```

不通过则打回 DEV 修复。

### 8.6 产品验收门禁

输入：

```text
prd-final.md
acceptance-report.md
test-report.md
security-validation-report.md
```

通过条件：

```text
PDM 验收通过
核心需求全部满足
验收问题全部关闭
用户需要确认的事项已确认
```

不通过则打回 DEV / TEST / PDM 处理。

---

## 9. 任务流转协议

每个任务应具备：

```json
{
  "id": "task_001",
  "project_id": "proj_001",
  "phase": "DEVELOPMENT",
  "owner_agent": "DEV",
  "title": "实现登录接口",
  "description": "根据 PRD 和详细设计实现登录接口。",
  "status": "pending",
  "priority": "normal",
  "input_artifacts": [],
  "expected_artifacts": [],
  "retry_count": 0,
  "max_retries": 3,
  "created_by": "PM",
  "assigned_to": "DEV",
  "blocked_by": [],
  "deadline": "2026-05-20T18:00:00+08:00"
}
```

任务状态：

```text
pending
assigned
running
waiting_review
failed
blocked
completed
cancelled
```

任务事件：

```text
TASK_CREATED
TASK_ASSIGNED
TASK_STARTED
TASK_RUN_FAILED
TASK_COMPLETED
TASK_REVIEW_FAILED
TASK_REVIEW_PASSED
TASK_ESCALATED
```

---

## 10. Claude Code CLI Runner 执行协议

### 10.1 Runner 职责

```text
接收 Agent 任务
创建隔离工作区
准备上下文文件
调用 Claude Code CLI
收集执行日志
收集代码 diff
收集测试结果
收集文档产物
回写数据库
通知 Hermes 当前任务完成
```

### 10.2 Runner 输入

```json
{
  "project_id": "proj_001",
  "task_id": "task_001",
  "task_run_id": "run_001",
  "agent": "developer",
  "phase": "development",
  "repo_path": "/repos/project-a",
  "workspace_path": "/workspaces/runs/run_001",
  "prompt": "根据 PRD 和详细设计实现功能。",
  "input_artifacts": [
    "docs/requirements/prd-final.md",
    "docs/design/detail-design-final.md"
  ],
  "expected_outputs": [
    "source_code_diff",
    "docs/dev/self-test-report.md"
  ],
  "constraints": [
    "不要修改需求范围外的模块",
    "完成后必须运行测试",
    "必须生成自测报告"
  ]
}
```

### 10.3 task-context.json

```json
{
  "project": {
    "id": "proj_001",
    "name": "用户登录功能",
    "phase": "DEVELOPMENT"
  },
  "agent": {
    "name": "DEV",
    "role": "开发工程师"
  },
  "task": {
    "id": "task_001",
    "title": "实现登录接口",
    "description": "根据 PRD 和详细设计实现登录接口。",
    "constraints": [
      "只能修改登录相关模块",
      "必须补充单元测试",
      "必须生成自测报告"
    ]
  },
  "input_artifacts": [
    "docs/requirements/prd-final.md",
    "docs/design/detail-design-final.md",
    "docs/design/api-design.md",
    "docs/dev/dev-design-notes.md"
  ],
  "expected_outputs": [
    "source_code_diff",
    "docs/dev/self-test-report.md",
    "docs/dev/implementation-notes.md"
  ]
}
```

### 10.4 DEV task-prompt.md 示例

```markdown
# Role

你是 DEV Agent，职责是完成编码实现、自测和开发文档沉淀。

# Task

根据输入产物实现登录接口。

# Inputs

- docs/requirements/prd-final.md
- docs/design/detail-design-final.md
- docs/design/api-design.md
- docs/dev/dev-design-notes.md

# Constraints

- 只能修改登录相关模块。
- 必须补充或更新单元测试。
- 必须运行相关测试。
- 必须生成 docs/dev/self-test-report.md。
- 如发现正式设计不合理，不得直接修改 detail-design-final.md，应写入 docs/design/design-change-requests.md。

# Expected Outputs

- 代码变更
- 单元测试结果
- 自测报告
- 实现说明
```

### 10.5 Claude Code CLI 调用方式

Runner 可采用非交互模式：

```bash
claude --model "$MODEL" --print < task-prompt.md
```

如果需要指定环境：

```bash
ANTHROPIC_BASE_URL="$BASE_URL" \
ANTHROPIC_API_KEY="$API_KEY" \
claude --model "$MODEL" --print < task-prompt.md
```

如果后续支持 OpenAI-compatible adapter，可以由 Runner 统一转换环境变量和模型参数。

### 10.6 Runner 输出

```json
{
  "task_run_id": "run_001",
  "status": "success",
  "summary": "登录接口实现完成，相关单测通过。",
  "changed_files": [
    "src/login/service.ts",
    "src/login/service.test.ts"
  ],
  "artifacts": [
    "docs/dev/self-test-report.md"
  ],
  "logs_path": "/logs/run_001.log",
  "diff_path": "/artifacts/proj_001/runs/run_001/diff.patch",
  "test_results": [
    {
      "command": "npm test",
      "status": "passed"
    }
  ]
}
```

执行后收集：

```text
stdout.log
stderr.log
changed-files.txt
diff.patch
result-summary.md
test-results.json
artifacts/
```

---

## 11. 模型配置设计

模型配置采用四层覆盖：

```text
全局默认配置
  < 全局 Agent 配置
  < 项目默认配置
  < 项目 Agent 配置
```

示例：

```yaml
model:
  defaults:
    provider: openai-compatible
    base_url: https://api.default.com/v1
    api_key_env: DEFAULT_MODEL_API_KEY
    model: claude-sonnet-4-6
    temperature: 0.2
    max_tokens: 8192
    timeout_seconds: 300
    max_retries: 2

  agents:
    architect:
      model: claude-opus-4-7
      timeout_seconds: 600

    developer:
      model: claude-opus-4-7
      timeout_seconds: 1200

projects:
  project_a:
    model:
      defaults:
        base_url: https://api.project-a.com/v1
        api_key_env: PROJECT_A_MODEL_API_KEY
        model: claude-sonnet-4-6

      agents:
        developer:
          base_url: https://api.dev-model.com/v1
          api_key_env: PROJECT_A_DEV_MODEL_API_KEY
          model: claude-opus-4-7
```

每个 Agent 支持：

```text
base_url
api_key
api_key_env
model
temperature
max_tokens
timeout_seconds
max_retries
```

不建议明文保存 `api_key`，优先使用 `api_key_env`。

---

## 12. 设计变更流程

### 12.1 触发条件

```text
DEV 发现设计无法实现
DEV 发现设计实现成本明显超预期
TEST 发现设计无法支撑测试验证
SEC 发现设计存在安全风险
ARCH 发现原设计存在缺陷
PDM 发现设计偏离 PRD
```

### 12.2 设计变更步骤

```text
1. 发现问题的 Agent 创建 DesignChangeRequest
2. PM 接收变更请求
3. ARCH 分析变更影响
4. PDM 判断是否影响需求范围
5. TEST 判断是否影响测试用例
6. SEC 判断是否影响安全要求
7. PM 汇总评审结果
8. 如果通过，ARCH 更新正式设计文档
9. 如果不通过，PM 将结论反馈给提出方
10. 如存在重大范围变化，PM 飞书通知用户确认
```

### 12.3 设计变更数据结构

```json
{
  "id": "dcr_001",
  "project_id": "proj_001",
  "source_agent": "DEV",
  "phase": "DEVELOPMENT",
  "title": "登录接口 token 刷新机制调整",
  "description": "原设计要求每次请求刷新 token，但实现后发现会造成并发覆盖问题。",
  "reason": "并发请求下 refresh token 存在覆盖风险。",
  "affected_artifacts": [
    "docs/design/detail-design-final.md",
    "docs/design/api-design.md",
    "docs/test/test-cases.md"
  ],
  "impact_analysis": {
    "requirement_impact": "none",
    "design_impact": "medium",
    "test_impact": "medium",
    "security_impact": "low"
  },
  "status": "pending_review",
  "created_at": "2026-05-17T10:00:00+08:00"
}
```

### 12.4 设计变更状态

```text
pending_review
reviewing
approved
rejected
user_confirmation_required
applied
cancelled
```

通过条件：

```text
ARCH 同意设计调整
PDM 确认不违背 PRD，或已同步修订需求
TEST 确认测试用例可同步调整
SEC 确认无不可接受安全风险
PM 确认项目计划可接受
```

---

## 13. 缺陷流转设计

缺陷来源包括：

```text
TEST 测试失败
SEC 安全验证失败
PDM 产品验收失败
DEV 自测失败
Claude Code CLI 执行失败
```

### 13.1 缺陷数据结构

```json
{
  "id": "bug_001",
  "project_id": "proj_001",
  "source": "TEST",
  "phase": "TEST_AND_SECURITY_VALIDATION",
  "title": "登录失败时返回码不符合 PRD",
  "description": "PRD 要求密码错误返回 401，当前返回 500。",
  "severity": "major",
  "priority": "high",
  "assigned_agent": "DEV",
  "related_artifacts": [
    "docs/requirements/prd-final.md",
    "docs/test/test-checklist.xlsx"
  ],
  "reproduce_steps": [
    "使用错误密码调用登录接口",
    "观察 HTTP 状态码"
  ],
  "expected_result": "返回 401",
  "actual_result": "返回 500",
  "status": "open",
  "retry_count": 0,
  "created_at": "2026-05-17T10:00:00+08:00"
}
```

### 13.2 缺陷状态

```text
open
assigned
fixing
fixed
retesting
verified
reopened
rejected
deferred
closed
```

### 13.3 缺陷流转

```text
TEST/SEC/PDM 创建缺陷
  ↓
PM 分派给 DEV
  ↓
DEV 修复
  ↓
DEV 自测
  ↓
TEST/SEC/PDM 复验
  ↓
通过：closed
失败：reopened，retry_count + 1
```

超过阈值：

```text
retry_count > max_retries
  -> EscalationManager 触发
  -> PM 飞书通知用户
  -> 当前缺陷进入 blocked
  -> 项目阶段进入 PAUSED 或 RISK_BLOCKED
```

### 13.4 缺陷严重级别

```text
blocker：阻塞主流程，无法继续测试或验收
critical：核心功能严重错误或高危安全问题
major：主要功能不符合预期
minor：轻微功能问题
trivial：文案、格式、低影响问题
```

---

## 14. 评审记录设计

### 14.1 评审类型

```text
requirement_review
design_review
testcase_review
design_change_review
security_review
acceptance_review
```

### 14.2 Review 数据结构

```json
{
  "id": "review_001",
  "project_id": "proj_001",
  "type": "design_review",
  "phase": "DESIGN_REVIEW",
  "round": 2,
  "status": "failed",
  "owner_agent": "ARCH",
  "participants": [
    "PM",
    "PDM",
    "DEV",
    "TEST",
    "SEC"
  ],
  "input_artifacts": [
    "docs/design/detail-design-draft.md",
    "docs/design/api-design.md",
    "docs/design/db-design.md"
  ],
  "conclusion": "failed",
  "created_at": "2026-05-17T10:00:00+08:00",
  "completed_at": "2026-05-17T11:00:00+08:00"
}
```

### 14.3 ReviewComment 数据结构

```json
{
  "id": "comment_001",
  "review_id": "review_001",
  "reviewer_agent": "SEC",
  "status": "fail",
  "severity": "major",
  "comment": "当前设计没有说明 token 存储和过期策略。",
  "required_change": "补充 token 存储位置、过期策略、刷新策略和失效策略。",
  "related_artifact": "docs/design/detail-design-draft.md",
  "created_at": "2026-05-17T10:30:00+08:00"
}
```

### 14.4 评审结论格式

```text
Status: pass / fail

Issues:
- ...

Required changes:
- ...

Risks:
- ...

Next step:
- ...
```

---

## 15. 异常升级机制

统一由 `EscalationManager` 管理。

### 15.1 默认规则

```yaml
escalation:
  default_max_retries: 3
  notify_channel: feishu
  notify_target: user

  policies:
    requirement_review_failed:
      max_retries: 3

    design_review_failed:
      max_retries: 3

    testcase_review_failed:
      max_retries: 3

    test_failed:
      max_retries: 3

    security_failed:
      max_retries: 3

    acceptance_failed:
      max_retries: 3

    task_execution_failed:
      max_retries: 2
```

### 15.2 异常类型

```text
review_failed_too_many_times
test_failed_too_many_times
security_failed_too_many_times
acceptance_failed_too_many_times
task_execution_failed_too_many_times
task_timeout
agent_output_invalid
cost_budget_exceeded
deadline_missed
manual_confirmation_required
```

### 15.3 Escalation 数据结构

```json
{
  "id": "esc_001",
  "project_id": "proj_001",
  "type": "test_failed_too_many_times",
  "phase": "TEST_AND_SECURITY_VALIDATION",
  "source_agent": "TEST",
  "target_user_id": "feishu_user_001",
  "status": "pending_user_decision",
  "retry_count": 3,
  "threshold": 3,
  "summary": "测试已连续 3 轮不通过。",
  "options": [
    {
      "key": "continue",
      "label": "继续自动修复一轮"
    },
    {
      "key": "redesign",
      "label": "暂停开发，重新评审设计"
    },
    {
      "key": "manual",
      "label": "人工介入排查"
    },
    {
      "key": "cancel",
      "label": "终止当前需求"
    }
  ],
  "created_at": "2026-05-17T10:00:00+08:00"
}
```

### 15.4 用户决策后的动作

| 用户选择 | 系统动作 |
|---|---|
| 继续自动修复一轮 | retry_count 阈值临时 +1，回到 BUG_FIXING |
| 重新评审设计 | 进入 DESIGN_REVIEW 或 DESIGN_CHANGE_REVIEW |
| 人工介入排查 | 项目进入 PAUSED，PM 等待人工结果 |
| 终止当前需求 | 项目或需求进入 CANCELLED |
| 修改需求范围 | 进入 REQUIREMENT_REVISION |

---

## 16. 飞书交互设计

用户只和 PM Agent 交互。

### 16.1 用户命令

建议支持：

```text
/创建项目
/查看项目状态
/查看当前阶段
/查看风险
/查看待我确认
/查看产物
/查看缺陷
/批准当前阶段
/驳回当前阶段
/暂停项目
/恢复项目
/终止项目
```

### 16.2 PM 主动通知场景

PM 只有在以下场景主动通知用户：

```text
需求存在根本歧义
阶段需要用户确认
失败次数超过阈值
项目进度明显延期
成本超过预算
存在高风险安全问题
产品验收需要确认
项目完成
```

### 16.3 项目状态消息

```text
项目：用户登录功能
当前阶段：测试与安全验证
状态：进行中

进展：
- DEV 已完成登录接口开发
- 自测和冒烟测试通过
- TEST 正在执行测试清单
- SEC 正在进行安全审查

风险：
- 暂无阻塞风险

下一步：
- 等待 TEST 和 SEC 输出验证结果
```

### 16.4 阶段评审待确认

```text
项目：用户登录功能
阶段：需求评审
状态：待确认

PRD 已完成需求评审，所有 Agent 均无阻塞问题。

产物：
- prd-final.md
- requirement-review.md

请确认是否批准进入详细设计阶段。

选项：
A. 批准
B. 驳回并补充意见
C. 暂停项目
```

### 16.5 异常升级消息

```text
项目：用户登录功能
阶段：测试验证
状态：异常阻塞

测试已连续 3 轮不通过，超过默认阈值。

主要问题：
1. 登录失败返回码不符合 PRD
2. 权限校验修复后出现回归
3. 测试环境数据初始化不稳定

已处理记录：
- 第 1 轮：DEV 修复参数校验
- 第 2 轮：DEV 修复权限判断
- 第 3 轮：TEST 复测仍失败

PM 建议：
A. 继续自动修复一轮
B. 暂停开发，重新评审设计
C. 人工介入排查
D. 终止当前需求

请确认下一步操作。
```

### 16.6 项目完成消息

```text
项目：用户登录功能
状态：已完成

完成内容：
- PRD 已确认
- 详细设计已评审通过
- 开发已完成
- 测试清单全部通过
- 安全验证通过
- 产品验收通过

主要产物：
- prd-final.md
- detail-design-final.md
- test-checklist.xlsx
- test-report.md
- security-validation-report.md
- acceptance-report.md

是否需要生成项目复盘报告？
```

---

## 17. Agent 间通信协议

Agent 之间不要随意自由聊天，建议通过结构化消息通信。

### 17.1 AgentMessage 数据结构

```json
{
  "id": "msg_001",
  "project_id": "proj_001",
  "from_agent": "DEV",
  "to_agent": "PDM",
  "message_type": "requirement_question",
  "phase": "DEVELOPMENT",
  "title": "登录失败是否需要区分账号不存在和密码错误",
  "content": "PRD 当前只说明登录失败返回错误提示，未明确是否需要区分账号不存在和密码错误。",
  "related_artifacts": [
    "docs/requirements/prd-final.md"
  ],
  "status": "pending",
  "created_at": "2026-05-17T10:00:00+08:00"
}
```

### 17.2 消息类型

```text
requirement_question
design_question
test_question
security_question
review_comment
change_request
defect_notice
fix_notice
validation_result
risk_notice
```

### 17.3 通信约束

```text
用户只与 PM 通信
其他 Agent 不直接联系用户
DEV 和 TEST 在设计与测试用例并行阶段不直接通信
需求问题统一发给 PDM
设计问题统一发给 ARCH
项目流程问题统一发给 PM
安全问题统一发给 SEC
测试问题统一发给 TEST
```

---

## 18. Agent 任务 Prompt 模板

### 18.1 通用模板

```markdown
# Role

你是 {{agent_role}}。

# Project

项目：{{project_name}}
当前阶段：{{phase}}

# Task

{{task_description}}

# Inputs

{{input_artifacts}}

# Constraints

{{constraints}}

# Expected Outputs

{{expected_outputs}}

# Output Format

请输出：
1. 执行摘要
2. 已完成内容
3. 产物路径
4. 风险或问题
5. 下一步建议
```

### 18.2 DEV Prompt 约束

```markdown
# Additional Rules for DEV

- 可以读写代码。
- 可以读写 docs/dev 下的开发设计文档。
- 可以读取 docs/design 下的正式设计文档。
- 不得直接修改 docs/design/detail-design-final.md。
- 如发现正式设计需要调整，写入 docs/design/design-change-requests.md。
- 修改代码后必须运行相关测试。
- 必须生成或更新 docs/dev/self-test-report.md。
```

### 18.3 TEST Prompt 约束

```markdown
# Additional Rules for TEST

- 根据 PRD 和测试用例执行验证。
- 不得修改业务代码。
- 测试失败必须记录到 test-checklist.xlsx 或 defect-report.md。
- 每个失败项必须包含复现步骤、期望结果、实际结果、严重级别。
- 验证修复时必须标记 defect 状态。
```

### 18.4 SEC Prompt 约束

```markdown
# Additional Rules for SEC

- 不得修改业务代码。
- 重点检查认证、授权、注入、敏感信息、依赖风险、配置风险。
- 安全问题必须记录严重级别和修复建议。
- 高危问题必须标记为 blocker 或 critical。
```

---

## 19. MVP 落地路线

### 19.1 阶段一：最小闭环

目标：先跑通一个完整小项目。

包含：

```text
飞书 Bot
PM Agent
PDM Agent
DEV Agent
TEST Agent
SQLite
任务队列
状态机
Claude Code CLI Runner
基础产物管理
异常重试计数
```

支持流程：

```text
创建项目
需求澄清
生成 PRD
开发实现
测试验证
缺陷修复
验收完成
```

暂不做：

```text
复杂安全审查
多项目并发
成本预算
完整权限系统
复杂 Agent 绩效统计
```

### 19.2 阶段二：工程化门禁

增加：

```text
ARCH Agent
SEC Agent
需求评审
详细设计评审
测试用例评审
安全验证
Git worktree 隔离
评审记录
缺陷状态机
```

### 19.3 阶段三：长期自治

增加：

```text
多项目并发
定时巡检
SLA
成本控制
任务恢复
失败自动归因
项目复盘报告
Agent 绩效统计
权限系统
审计日志
```

---

## 20. 最终方案一句话

这是一个以 Hermes Agent 为项目大脑、以 PM Agent 为用户唯一入口、以 Claude Code CLI Runner 为统一执行器、以状态机和数据库为长期记忆与事实源的异步多 Agent 软件工程团队平台。
