from app.rate_limit import InMemoryRateLimiter


def test_rate_limiter_rejects_after_limit() -> None:
    limiter = InMemoryRateLimiter(limit=2, window_seconds=60)

    assert limiter.allow("client") is True
    assert limiter.allow("client") is True
    assert limiter.allow("client") is False
    assert limiter.allow("other-client") is True
