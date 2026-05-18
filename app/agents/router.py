from fastapi import APIRouter, Request

from app.agents import service
from app.agents.schemas import AgentCreateRequest, AgentEnabledRequest
from app.core.responses import success_response

router = APIRouter()


def _database_path(request: Request) -> str:
    return request.app.state.database_path


def _config_path(request: Request):
    return request.app.state.config_path


@router.post("/api/agents")
def create_agent(request_body: AgentCreateRequest, request: Request):
    return success_response(service.create_agent(_database_path(request), request_body))


@router.get("/api/agents")
def list_agents(request: Request, enabled: bool | None = None):
    return success_response(service.list_agents(_database_path(request), enabled))


@router.post("/api/agents/bootstrap-defaults")
def bootstrap_default_agents(request: Request):
    return success_response(service.bootstrap_default_agents(_database_path(request)))


@router.get("/api/agents/{agent_id}")
def get_agent(agent_id: str, request: Request):
    return success_response(service.get_agent(_database_path(request), agent_id))


@router.post("/api/agents/{agent_id}/enabled")
def set_agent_enabled(agent_id: str, request_body: AgentEnabledRequest, request: Request):
    return success_response(service.set_agent_enabled(_database_path(request), agent_id, request_body.enabled))


@router.get("/api/agents/{agent_name}/model-config")
def get_agent_model_config(agent_name: str, request: Request):
    return success_response(service.resolve_agent_model_config(_config_path(request), agent_name))
