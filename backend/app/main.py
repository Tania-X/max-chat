from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.shared.config import get_settings
from app.shared.database import init_db
from app.shared.exceptions import register_exception_handlers
from app.shared.secrets_store import ensure_secrets


class SPAStaticFiles(StaticFiles):
    """SPA 回退：非 /api 路径找不到文件时返回 index.html。"""

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 启动阶段即完成密钥解析/生成，避免首个请求时才暴露配置问题
    ensure_secrets()
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

    static_dir = Path(__file__).resolve().parent.parent / "static"
    if static_dir.exists():
        app.mount("/", SPAStaticFiles(directory=static_dir, html=True), name="spa")
    return app


app = create_app()
