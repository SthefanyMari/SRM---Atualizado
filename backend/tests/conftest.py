import os


try:
    import aiosqlite  # noqa: F401
except ModuleNotFoundError:
    pass
else:
    os.environ["DATABASE_URL"] = os.environ.get(
        "TEST_DATABASE_URL",
        "sqlite+aiosqlite:////tmp/recomendacao_api_test.db",
    )
os.environ["APP_ENVIRONMENT"] = "testing"
