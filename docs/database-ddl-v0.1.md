# 数据库 DDL 设计 v0.1

## 1. 设计目标

MVP 阶段数据库用于承载长期项目状态、任务执行记录、评审记录、缺陷记录、异常升级、Agent 间消息和产物索引。

初期建议使用 SQLite，DDL 尽量保持与 Postgres 兼容，便于后续迁移。

---

## 2. 表清单

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

---

## 3. DDL

### 3.1 projects

```sql
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    owner_user_id TEXT NOT NULL,
    repo_url TEXT,
    default_branch TEXT DEFAULT 'main',
    status TEXT NOT NULL DEFAULT 'active',
    current_phase TEXT NOT NULL DEFAULT 'INIT',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX idx_projects_owner_user_id ON projects(owner_user_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_current_phase ON projects(current_phase);
```

---

### 3.2 project_events

```sql
CREATE TABLE project_events (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor_type TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    payload_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE INDEX idx_project_events_project_id ON project_events(project_id);
CREATE INDEX idx_project_events_event_type ON project_events(event_type);
CREATE INDEX idx_project_events_created_at ON project_events(created_at);
```

---

### 3.3 agents

```sql
CREATE TABLE agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL,
    description TEXT,
    enabled INTEGER NOT NULL DEFAULT 1,
    model_config_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX idx_agents_enabled ON agents(enabled);
```

---

### 3.4 tasks

```sql
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    phase TEXT NOT NULL,
    owner_agent TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    priority TEXT NOT NULL DEFAULT 'normal',
    input_artifacts_json TEXT,
    expected_artifacts_json TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    created_by TEXT NOT NULL,
    assigned_to TEXT,
    blocked_by_json TEXT,
    deadline TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE INDEX idx_tasks_project_id ON tasks(project_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_phase ON tasks(phase);
CREATE INDEX idx_tasks_owner_agent ON tasks(owner_agent);
```

---

### 3.5 task_runs

```sql
CREATE TABLE task_runs (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    runner_type TEXT NOT NULL DEFAULT 'claude_code_cli',
    workspace_path TEXT,
    workspace_strategy TEXT,
    status TEXT NOT NULL DEFAULT 'created',
    started_at TEXT,
    finished_at TEXT,
    logs_path TEXT,
    stdout_path TEXT,
    stderr_path TEXT,
    diff_path TEXT,
    summary TEXT,
    error_type TEXT,
    error_message TEXT,
    result_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE INDEX idx_task_runs_task_id ON task_runs(task_id);
CREATE INDEX idx_task_runs_project_id ON task_runs(project_id);
CREATE INDEX idx_task_runs_status ON task_runs(status);
```

---

### 3.6 artifacts

```sql
CREATE TABLE artifacts (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    task_id TEXT,
    artifact_type TEXT NOT NULL,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT 'v1',
    status TEXT NOT NULL DEFAULT 'active',
    created_by TEXT NOT NULL,
    metadata_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

CREATE INDEX idx_artifacts_project_id ON artifacts(project_id);
CREATE INDEX idx_artifacts_task_id ON artifacts(task_id);
CREATE INDEX idx_artifacts_type ON artifacts(artifact_type);
```

---

### 3.7 reviews

```sql
CREATE TABLE reviews (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    type TEXT NOT NULL,
    phase TEXT NOT NULL,
    round INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'open',
    owner_agent TEXT NOT NULL,
    participants_json TEXT NOT NULL,
    input_artifacts_json TEXT,
    conclusion TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE INDEX idx_reviews_project_id ON reviews(project_id);
CREATE INDEX idx_reviews_type ON reviews(type);
CREATE INDEX idx_reviews_status ON reviews(status);
```

---

### 3.8 review_comments

```sql
CREATE TABLE review_comments (
    id TEXT PRIMARY KEY,
    review_id TEXT NOT NULL,
    reviewer_agent TEXT NOT NULL,
    status TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'minor',
    comment TEXT NOT NULL,
    required_change TEXT,
    related_artifact TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (review_id) REFERENCES reviews(id)
);

CREATE INDEX idx_review_comments_review_id ON review_comments(review_id);
CREATE INDEX idx_review_comments_reviewer_agent ON review_comments(reviewer_agent);
CREATE INDEX idx_review_comments_status ON review_comments(status);
```

---

### 3.9 issues

```sql
CREATE TABLE issues (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    source TEXT NOT NULL,
    phase TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    severity TEXT NOT NULL DEFAULT 'major',
    priority TEXT NOT NULL DEFAULT 'normal',
    assigned_agent TEXT,
    related_artifacts_json TEXT,
    reproduce_steps_json TEXT,
    expected_result TEXT,
    actual_result TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE INDEX idx_issues_project_id ON issues(project_id);
CREATE INDEX idx_issues_status ON issues(status);
CREATE INDEX idx_issues_severity ON issues(severity);
CREATE INDEX idx_issues_assigned_agent ON issues(assigned_agent);
```

---

### 3.10 escalations

```sql
CREATE TABLE escalations (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    type TEXT NOT NULL,
    phase TEXT NOT NULL,
    source_agent TEXT,
    target_user_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending_user_decision',
    retry_count INTEGER NOT NULL,
    threshold INTEGER NOT NULL,
    summary TEXT NOT NULL,
    options_json TEXT NOT NULL,
    decision TEXT,
    decision_comment TEXT,
    decided_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE INDEX idx_escalations_project_id ON escalations(project_id);
CREATE INDEX idx_escalations_status ON escalations(status);
CREATE INDEX idx_escalations_type ON escalations(type);
```

---

### 3.11 agent_messages

```sql
CREATE TABLE agent_messages (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    from_agent TEXT NOT NULL,
    to_agent TEXT NOT NULL,
    message_type TEXT NOT NULL,
    phase TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    related_artifacts_json TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE INDEX idx_agent_messages_project_id ON agent_messages(project_id);
CREATE INDEX idx_agent_messages_to_agent ON agent_messages(to_agent);
CREATE INDEX idx_agent_messages_status ON agent_messages(status);
CREATE INDEX idx_agent_messages_type ON agent_messages(message_type);
```

---

## 4. 枚举建议

### 4.1 project.status

```text
active
paused
failed
cancelled
done
```

### 4.2 task.status

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

### 4.3 task_run.status

```text
created
preparing_workspace
building_context
running_claude
collecting_results
parsing_output
completed
failed
timeout
cancelled
```

### 4.4 review.status

```text
open
passed
failed
cancelled
```

### 4.5 issue.status

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
blocked
```
