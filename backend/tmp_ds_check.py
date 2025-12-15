from src.app.data.database import SessionLocal
from src.app.services.query_context import create_query_context

session = SessionLocal()
ctx = create_query_context(session, "default_tenant", "test_user")
print("tenant:", ctx.tenant_id)
print("data sources:", [(ds.id, ds.name, ds.status.value) for ds in ctx.get_tenant_data_sources()])
session.close()


