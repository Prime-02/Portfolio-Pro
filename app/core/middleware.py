from fastapi import Request

async def log_requests(request: Request, call_next):
    # Log request details
    response = await call_next(request)
    return response