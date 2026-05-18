from app.projects import service as project_service
from app.workflows.schemas import WorkflowTransitionRequest
from app.workflows.state_machine import allowed_transitions, can_transition


class WorkflowError(ValueError):
    pass


def get_workflow(database_path: str, project_id: str):
    project = project_service.get_project(database_path, project_id)
    if project is None:
        return None
    return {
        "project_id": project_id,
        "current_phase": project["current_phase"],
        "allowed_transitions": allowed_transitions(project["current_phase"]),
    }


def _transition(database_path: str, project_id: str, request: WorkflowTransitionRequest, event_type: str):
    project = project_service.get_project(database_path, project_id)
    if project is None:
        raise WorkflowError("项目不存在")
    if project["current_phase"] != request.from_phase:
        raise WorkflowError("from_phase 与当前项目阶段不一致")
    if not can_transition(request.from_phase, request.to_phase):
        raise WorkflowError("目标阶段不允许从当前阶段进入")
    project_service.update_project_phase(
        database_path,
        project_id,
        request.from_phase,
        request.to_phase,
        event_type,
        request.reason,
        request.evidence,
    )
    return get_workflow(database_path, project_id)


def advance_workflow(database_path: str, project_id: str, request: WorkflowTransitionRequest):
    return _transition(database_path, project_id, request, "workflow_advanced")


def transition_workflow(database_path: str, project_id: str, request: WorkflowTransitionRequest):
    return _transition(database_path, project_id, request, "workflow_transitioned")


def reject_workflow(database_path: str, project_id: str, request: WorkflowTransitionRequest):
    return _transition(database_path, project_id, request, "workflow_rejected")
