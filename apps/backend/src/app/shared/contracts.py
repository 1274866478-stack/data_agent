from typing import Any, Dict, Optional, Protocol


class AgentV2GatewayProtocol(Protocol):
    """Boundary contract for all backend -> agentv2 calls."""

    def is_available(self) -> bool:
        ...

    async def run_legacy_query(
        self,
        *,
        question: str,
        thread_id: str,
        connection_id: Optional[str],
        tenant_id: Optional[str],
        user_id: Optional[str],
        session_id: Optional[str],
        db_session: Any,
        db_type: str,
    ) -> Dict[str, Any]:
        ...

