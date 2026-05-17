from fastapi import FastAPI

from app.artifacts.router import router as artifacts_router
from app.core.database import init_db
from app.core.responses import success_response
from app.escalations.router import router as escalations_router
from app.issues.router import router as issues_router
from app.messaging.router import router as messaging_router
from app.projects.router import router as projects_router
from app.reviews.router import router as reviews_router
from app.runners.router import router as runners_router
from app.tasks.router import router as tasks_router
from app.workflows.router import router as workflows_router


def create_app(database_path: str = "data/app.db") -> FastAPI:
    app = FastAPI(title="Hermes Agent Software Team")
    app.state.database_path = database_path
    init_db(database_path)

    @app.get("/health")
    def health():
        return success_response({"status": "ok"})

    app.include_router(projects_router)
    app.include_router(tasks_router)
    app.include_router(workflows_router)
    app.include_router(reviews_router)
    app.include_router(artifacts_router)
    app.include_router(escalations_router)
    app.include_router(issues_router)
    app.include_router(messaging_router)
    app.include_router(runners_router)
    return app


app = create_app()
