from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse
from fastapi import status
from app.schemas import ErrorResponse, ErrorDetails, MetaData

limiter = Limiter(key_func=get_remote_address)

async def rate_limit_handler(request, exc: RateLimitExceeded):
    
    message = exc.detail.split(" ")
    every, unit = message[2], message[3]
    
    error_details = ErrorDetails(
            type="Rate limit exceeded",
            message=f"You have exceeded the allowed number of requests. Please try again after {every} {unit}",
            details=None
        )
    
    meta_data = MetaData(
        request_id=request.headers.get("request-id", "default_request_id"),
        client=request.headers.get("client-type", "unknown")
    )
    
    error_response = ErrorResponse(
        status="error",
        message=error_details.message,
        data=error_details,
        meta=meta_data
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )
