from uuid import uuid4


def success_response(data):
    return {
        "success": True,
        "data": data,
        "request_id": f"req_{uuid4().hex}",
    }


def error_response(code: str, message: str):
    return {
        "success": False,
        "error": {"code": code, "message": message},
        "request_id": f"req_{uuid4().hex}",
    }
