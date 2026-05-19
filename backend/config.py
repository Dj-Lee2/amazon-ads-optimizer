import os

_db_path = os.path.join(os.path.dirname(__file__), "optimizer.db")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{_db_path}",
)
DATA_PROVIDER = os.getenv("DATA_PROVIDER", "mock")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
