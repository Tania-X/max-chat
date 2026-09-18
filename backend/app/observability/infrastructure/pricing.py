# 每百万 token 定价 (input, output)，单位 USD
PRICING: dict[str, tuple[float, float]] = {
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-2.0-flash-lite": (0.075, 0.30),
    "gemini-1.5-pro": (1.25, 5.00),
    "gemini-1.5-flash": (0.075, 0.30),
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "claude-3-5-sonnet-20241022": (3.00, 15.00),
    "claude-3-5-haiku-20241022": (0.80, 4.00),
    "deepseek-chat": (0.27, 1.10),
    "deepseek-reasoner": (0.55, 2.19),
}

DEFAULT_PRICE = (0.50, 1.50)


def estimate_cost(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    price = PRICING.get(model_name)
    if price is None:
        matched = [v for k, v in PRICING.items() if k in model_name or model_name in k]
        price = matched[0] if matched else DEFAULT_PRICE
    cost = prompt_tokens / 1_000_000 * price[0] + completion_tokens / 1_000_000 * price[1]
    return round(cost, 8)
