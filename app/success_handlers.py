from typing import Any

from fastapi import Request

from app.schemas import schemas


def success_response(message: str, attatched_data: Any, request: Request = None):
    return schemas.SuccessResponse(
        status="success",
        message=message,
        data=attatched_data,
        meta={
            "request_id": request.headers.get("request-id", "default_request_id"),
            "client": request.headers.get("client-type", "unknown"),
        },
    )
