from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_config
from dependencies import (
    cleanup_dependencies,
    get_process_message_use_case,
    init_dependencies,
)
from src.adapters.inbound.agent_router import (
    get_process_message_use_case as _router_stub,
    router,
)

_ALLOWED_ORIGINS = [o.strip() for o in os.getenv("AI_AGENT_ALLOWED_ORIGIN", "*").split(",")]


def _configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(format="%(message)s", level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _configure_logging()
    cfg = get_config()
    await init_dependencies(cfg)
    yield
    await cleanup_dependencies()


app = FastAPI(title="Participa AI — Agent Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(router)

# Reemplaza el stub del router con la implementación real del contenedor de DI
app.dependency_overrides[_router_stub] = get_process_message_use_case
