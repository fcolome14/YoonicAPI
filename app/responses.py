
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import HTTPException, Request, status

from app.schemas.schemas import ErrorDetails, SuccessResponse, InternalResponse

class SuccessHTTPResponse:
    def success_response(message: str, attatched_data: Any, request: Request = None):
        return SuccessResponse(
            status="success",
            message=message,
            data=attatched_data,
            meta={
                "request_id": request.headers.get("request-id", "default_request_id"),
                "client": request.headers.get("client-type", "unknown"),
            },
        )

class ErrorHTTPResponse:
    def error_response(type: str, status_code: status, message: str, details: str):
        raise HTTPException(
            status_code=status_code,
            detail=ErrorDetails(
                type=type,
                message=message,
                details=details,
            ).model_dump(),
        )

class SystemResponse:
    def internal_response(status: Enum, origin, message):
        return InternalResponse(
            status=status,
            origin=origin,
            message=message,
            timestamp=datetime.now().isoformat()
        )