import asyncio
import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

import app.models
from app.database import Base, engine
from app.websocket.timeout_checker import run_offline_timeout_checker

from app.routes.auth_router import router as auth_router
from app.routes.computer_router import router as computer_router
from app.routes.agent_router import router as agent_router
from app.routes.websocket_router import router as websocket_router
from app.routes.enrollment_router import router as enrollment_router
from app.routes.metric_router import router as metric_router
from app.routes.command_router import router as command_router
from app.routes.notification_router import router as notification_router

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

Base.metadata.create_all(bind=engine)

API_PREFIX = "/api"

app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(computer_router, prefix=API_PREFIX)
app.include_router(agent_router, prefix=API_PREFIX)
app.include_router(enrollment_router, prefix=API_PREFIX)
app.include_router(metric_router, prefix=API_PREFIX)
app.include_router(websocket_router)
app.include_router(notification_router, prefix=API_PREFIX)
app.include_router(command_router, prefix=API_PREFIX)



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
            "detail": "An unexcepted error occurred.",
            "error_code": "INTERNAL_ERROR"
        }
    )


@app.get("/")
async def home():
    return {"message":"SLMS Backend is running"}