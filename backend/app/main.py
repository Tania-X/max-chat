from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.shared.config import get_settings
from app.shared.database import init_db
from app.shared.exceptions import register_exception_handlers

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="MAX Chat", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)

    from app.agent_runtime.interfaces.router import router as models_router
    from app.capability.interfaces.router import router as capabilities_router
    from app.conversation.interfaces.router import router as conversation_router
    from app.identity.interfaces.router import router as auth_router
    from app.memory.interfaces.router import router as memory_router
    from app.observability.interfaces.router import router as observability_router

    app.include_router(auth_router)
    app.include_router(conversation_router)
    app.include_router(models_router)
    app.include_router(memory_router)
    app.include_router(capabilities_router)
    app.include_router(observability_router)
    return app


app = create_app()
