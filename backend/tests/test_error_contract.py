"""错误响应契约测试：统一 {detail, code}。"""


async def test_validation_error_follows_detail_code_contract(client):
    """422 也必须遵守契约，且 detail 是可读字符串。

    修复前 FastAPI 默认返回 {"detail": [ {...} ]}，前端会渲染成 [object Object]。
    """
    resp = await client.post("/api/auth/register", json={"username": "u", "password": "123"})

    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "validation_error"
    assert isinstance(body["detail"], str) and body["detail"]
    # 字段级信息仍然保留，便于排查
    assert isinstance(body.get("errors"), list) and body["errors"]
    assert {"loc", "msg", "type"} <= set(body["errors"][0])


async def test_domain_error_keeps_contract(client):
    """既有 DomainError 契约不受影响。"""
    resp = await client.get("/api/sessions")

    assert resp.status_code == 401
    assert resp.json() == {"detail": "未登录", "code": "unauthorized"}
