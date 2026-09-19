import time
import uuid

from app.agent_runtime.domain.models import ModelConfig
from app.agent_runtime.domain.repository import ModelConfigRepository
from app.agent_runtime.infrastructure.model_factory import resolve_api_key, validate_base_url
from app.shared.exceptions import ForbiddenError, NotFoundError


def _redact(text: str, secret: str) -> str:
    """从第三方错误信息中抹掉 Key，避免凭据随错误回显。"""
    if not secret or len(secret) < 8:
        return text
    return text.replace(secret, "***")


class ModelConfigService:
    def __init__(self, repo: ModelConfigRepository):
        self.repo = repo

    async def list(self, user_id: str) -> list[ModelConfig]:
        return await self.repo.list_by_user(user_id)

    async def create(self, user_id: str, data: dict) -> ModelConfig:
        validate_base_url(data.get("base_url", ""))
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
        if "base_url" in data and data["base_url"] is not None:
            validate_base_url(data["base_url"])
        for field in ("provider", "model_name", "base_url", "label"):
            if field in data and data[field] is not None:
                setattr(config, field, data[field])
        if not config.label:
            config.label = f"{config.provider}/{config.model_name}"
        if data.get("api_key"):
            config.api_key = data["api_key"]
        if "is_default" in data and data["is_default"] is not None:
            config.is_default = bool(data["is_default"])
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
        validate_base_url(config.base_url)
        api_key = resolve_api_key(config)
        model = (
            f"gemini/{config.model_name}"
            if config.provider == "gemini"
            else f"{config.provider}/{config.model_name}"
        )
        call_kwargs: dict = {}
        if api_key:
            call_kwargs["api_key"] = api_key
        if config.base_url:
            call_kwargs["api_base"] = config.base_url
        start = time.perf_counter()
        try:
            import litellm

            resp = await litellm.acompletion(
                model=model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
                **call_kwargs,
            )
            latency = round((time.perf_counter() - start) * 1000)
            return {"ok": True, "latency_ms": latency, "model": resp.model}
        except Exception as exc:
            # 第三方异常原文可能回显 Key，落库/回显前先脱敏
            return {"ok": False, "error": _redact(str(exc), api_key)}

    async def _get_owned(self, user_id: str, config_id: str) -> ModelConfig:
        config = await self.repo.get(config_id)
        if not config:
            raise NotFoundError("模型配置不存在")
        if config.user_id != user_id:
            raise ForbiddenError("无权操作该配置")
        return config
