"""
Tenants domain facade.
"""

from .service import TenantService, TenantSetupService, get_tenant_service, get_tenant_setup_service, tenant_service
from .config_manager import tenant_config_manager, ProviderType

__all__ = [
    "TenantService",
    "TenantSetupService",
    "get_tenant_service",
    "get_tenant_setup_service",
    "tenant_service",
    "tenant_config_manager",
    "ProviderType",
]
