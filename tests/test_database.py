import sqlite3

from app.core.database import get_connection, init_db


def test_init_db_creates_mvp_tables_and_indexes(tmp_path):
    database_path = tmp_path / "app.db"

    init_db(str(database_path))

    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        indexes = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            ).fetchall()
        }

    assert {
        "projects",
        "project_events",
        "agents",
        "tasks",
        "task_runs",
        "artifacts",
        "reviews",
        "review_comments",
        "issues",
        "escalations",
        "agent_messages",
        "feishu_notifications",
    }.issubset(tables)
    assert {"idx_projects_status", "idx_tasks_project_id", "idx_task_runs_status"}.issubset(indexes)


def test_get_connection_enables_foreign_keys(tmp_path):
    database_path = tmp_path / "app.db"

    connection = get_connection(str(database_path))

    assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    connection.close()
