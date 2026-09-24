import asyncio
import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

import app.models
from app.websocket.timeout_checker import run_offline_timeout_checker

from app.routes.auth_router import router as auth_router
from app.routes.computer_router import router as computer_router
from app.routes.agent_router import router as agent_router
from app.routes.websocket_router import router as websocket_router
from app.routes.enrollment_router import router as enrollment_router
from app.routes.metric_router import router as metric_router
from app.routes.command_router import router as command_router
from app.routes.notification_router import router as notification_router
from app.routes.software_router import router as software_router
from app.routes.usage_router import router as usage_router
from app.routes.issue_router import router as issue_router
from app.routes.maintenance_router import router as maintenance_router
from app.routes.user_router import router as user_router

logger = logging.getLogger("slms")

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(run_offline_timeout_checker())

    try:
        yield
    finally:
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

    # Shutdown
    print("Application is shutting down...")

app = FastAPI(
    title="Smart Lab Management System",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api"

app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(computer_router, prefix=API_PREFIX)
app.include_router(agent_router, prefix=API_PREFIX)
app.include_router(enrollment_router, prefix=API_PREFIX)
app.include_router(metric_router, prefix=API_PREFIX)
app.include_router(websocket_router)
app.include_router(notification_router, prefix=API_PREFIX)
app.include_router(command_router, prefix=API_PREFIX)
app.include_router(software_router, prefix=API_PREFIX)
app.include_router(usage_router,prefix=API_PREFIX)
app.include_router(issue_router, prefix=API_PREFIX)
app.include_router(maintenance_router, prefix=API_PREFIX)
app.include_router(user_router, prefix=API_PREFIX)

# ---- Global exception handlers ----

@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    logger.warning(f"IntegrityError on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "detail": "Request conflicts with existing data.",
            "error_code": "INTEGRITY_ERROR"
        }
    )

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"SQLAlchemyError on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "A database error occurred",
            "error_code": "DATABASE_ERROR"
        }
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception on {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An unexpected error occurred.",
            "error_code": "INTERNAL_ERROR"
        }
    )


@app.get("/")
async def home():
    return {"message":"SLMS Backend is running"}