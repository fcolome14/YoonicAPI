""" Customized error handling response structure """

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from app.schemas import ErrorResponse, ErrorDetails, MetaData

def custom_http_exception_handler(request: Request, exc: HTTPException):
    
    exc_detail = exc.detail
    
    error_details = ErrorDetails(
        type=exc_detail.get("type"),
        message=exc_detail.get("message"), 
        details=exc_detail.get("details")
    )
    #TODO: REMOVE MESSAGE
    
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
