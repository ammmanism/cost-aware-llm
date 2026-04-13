class TenantIsolation:
    """Ensures data and resource isolation between tenants."""
    def get_tenant_context(self, tenant_id: str):
        return {"tenant_id": tenant_id, "namespace": f"res_{tenant_id}"}
