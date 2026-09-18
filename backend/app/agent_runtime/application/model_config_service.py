import time
import uuid

from app.agent_runtime.domain.models import ModelConfig
from app.agent_runtime.domain.repository import ModelConfigRepository
from app.agent_runtime.infrastructure.model_factory import apply_model_env
from app.shared.exceptions import ForbiddenError, NotFoundError


class ModelConfigService:
    def __init__(self, repo: ModelConfigRepository):
        self.repo = repo

    async def list(self, user_id: str) -> list[ModelConfig]:
        return await self.repo.list_by_user(user_id)

    async def create(self, user_id: str, data: dict) -> ModelConfig:
        config = ModelConfig(
            id=str(uuid.uuid4()),
            user_id=user_id,
            provider=data["provider"],
            model_name=data["model_name"],
            api_key=data.get("api_key", ""),
            base_url=data.get("base_url", ""),
            label=data.get("label", "") or f"{data['provider']}/{data['model_name']}",
            is_default=data.get("is_default", False),
        )
        return await self.repo.save(config)

    async def update(self, user_id: str, config_id: str, data: dict) -> ModelConfig:
        config = await self._get_owned(user_id, config_id)
        for field in ("provider", "model_name", "base_url", "label"):
            if field in data and data[field] is not None:
                setattr(config, field, data[field])
        if data.get("api_key"):
            config.api_key = data["api_key"]
        if data.get("is_default"):
            config.is_default = True
        return await self.repo.save(config)

    async def delete(self, user_id: str, config_id: str) -> None:
        await self._get_owned(user_id, config_id)
        await self.repo.delete(config_id)

    async def resolve_for_chat(self, user_id: str, config_id: str | None) -> ModelConfig | None:
        if config_id:
            config = await self.repo.get(config_id)
            if config and config.user_id == user_id:
                return config
        return await self.repo.get_default(user_id)

    async def test_connection(self, config: ModelConfig) -> dict:
        apply_model_env(config)
        model = (
            f"gemini/{config.model_name}"
            if config.provider == "gemini"
            else f"{config.provider}/{config.model_name}"
        )
        start = time.perf_counter()
        try:
            import litellm

            resp = await litellm.acompletion(
                model=model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            latency = round((time.perf_counter() - start) * 1000)
            return {"ok": True, "latency_ms": latency, "model": resp.model}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    async def _get_owned(self, user_id: str, config_id: str) -> ModelConfig:
        config = await self.repo.get(config_id)
        if not config:
            raise NotFoundError("模型配置不存在")
        if config.user_id != user_id:
            raise ForbiddenError("无权操作该配置")
        return config
