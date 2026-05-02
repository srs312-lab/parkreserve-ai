from app.config.settings import settings
from app.db.memory_store import MemoryStore
from app.db.postgres_store import PostgresStore


def _build_store() -> MemoryStore:
    postgres_store = PostgresStore(settings.database_url)
    if postgres_store.is_available():
        postgres_store.initialize()
        return postgres_store

    print("Postgres is unavailable; using in-memory store.")
    return MemoryStore()


store = _build_store()


def store_backend_name() -> str:
    return type(store).__name__
