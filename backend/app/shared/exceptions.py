from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class DomainError(Exception):
    status_code = 400
    code = "domain_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    status_code = 404
    code = "not_found"


class AuthError(DomainError):
    status_code = 401
    code = "unauthorized"


class ConflictError(DomainError):
    status_code = 409
    code = "conflict"


class ForbiddenError(DomainError):
    status_code = 403
    code = "forbidden"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "code": exc.code},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        """让 422 也遵守 {detail, code} 契约。

        FastAPI 默认返回 {"detail": [ {...} ]}，前端拿到数组会渲染成
        [object Object]；这里把 detail 归一为可读字符串，字段级信息放进 errors。
        """
        errors = [
            {
                "loc": [str(part) for part in err.get("loc", ())],
                "msg": err.get("msg", ""),
                "type": err.get("type", ""),
            }
            for err in exc.errors()
        ]
        first = errors[0]["msg"] if errors else "请求参数不合法"
        return JSONResponse(
            status_code=422,
            content=jsonable_encoder(
                {"detail": first, "code": "validation_error", "errors": errors}
            ),
        )
