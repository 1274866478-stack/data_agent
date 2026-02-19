from src.app.services.query_context import get_query_context


class QueryContextService:
    """Thin adapter for query context orchestration."""

    @staticmethod
    def create(db, tenant_id: str, user_id: str):
        return get_query_context(db, tenant_id, user_id)

