from app.settings import Settings


def test_allowed_origins_are_parsed() -> None:
    settings = Settings(allowed_origins="http://localhost:3000, https://platform.example")

    assert settings.cors_origins == [
        "http://localhost:3000",
        "https://platform.example",
    ]
