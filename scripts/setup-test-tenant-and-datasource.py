#!/usr/bin/env python3
"""
设置测试租户和数据源
"""

import asyncio
import sys
import os

# 添加backend到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.app.data.models import Tenant, DataSourceConnection, DataSourceConnectionStatus, TenantStatus
from src.app.services.encryption_service import encryption_service
import uuid
from datetime import datetime

# 数据库连接
DATABASE_URL = "postgresql://postgres:password@localhost:5432/dataagent"

def setup_tenant_and_datasource():
    """设置测试租户和数据源"""
    print("=" * 60)
    print("  设置测试租户和数据源")
    print("=" * 60)
    print()
    
    # 创建数据库引擎
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 1. 检查或创建默认租户
        tenant_id = "default_tenant"
        tenant = session.query(Tenant).filter(Tenant.id == tenant_id).first()
        
        if not tenant:
            print(f"📝 创建默认租户: {tenant_id}")
            tenant = Tenant(
                id=tenant_id,
                display_name="默认租户",
                email="admin@dataagent.local",
                status=TenantStatus.ACTIVE,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(tenant)
            session.commit()
            print("✅ 租户创建成功")
        else:
            print(f"✅ 租户已存在: {tenant.display_name or tenant.email}")
        
        print()
        
        # 2. 检查或创建数据源
        datasource_name = "ChatBI测试数据库"
        existing_ds = session.query(DataSourceConnection).filter(
            DataSourceConnection.tenant_id == tenant_id,
            DataSourceConnection.name == datasource_name
        ).first()
        
        if existing_ds:
            print(f"⚠️  数据源已存在: {existing_ds.name}")
            print(f"   ID: {existing_ds.id}")
            print(f"   状态: {existing_ds.status}")
            
            # 更新为激活状态
            if existing_ds.status != DataSourceConnectionStatus.ACTIVE:
                existing_ds.status = DataSourceConnectionStatus.ACTIVE
                session.commit()
                print("✅ 已更新为激活状态")
        else:
            print(f"📝 创建数据源: {datasource_name}")
            
            # 连接字符串（使用Docker网络内的主机名）
            connection_string = "postgresql://postgres:password@db:5432/chatbi_test"
            
            # 加密连接字符串
            encrypted_string = encryption_service.encrypt_connection_string(connection_string)
            
            # 创建数据源
            datasource = DataSourceConnection(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                name=datasource_name,
                db_type="postgresql",
                connection_string=encrypted_string,
                host="db",
                port=5432,
                database_name="chatbi_test",
                status=DataSourceConnectionStatus.ACTIVE,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            session.add(datasource)
            session.commit()
            
            print("✅ 数据源创建成功")
            print(f"   ID: {datasource.id}")
            print(f"   类型: {datasource.db_type}")
            print(f"   数据库: {datasource.database_name}")
        
        print()
        
        # 3. 列出所有数据源
        print("📋 当前数据源列表:")
        all_datasources = session.query(DataSourceConnection).filter(
            DataSourceConnection.tenant_id == tenant_id
        ).all()
        
        for ds in all_datasources:
            status_icon = "✅" if ds.is_active else "❌"
            print(f"   {status_icon} {ds.name} ({ds.db_type}) - {ds.status}")
        
        print()
        print("=" * 60)
        print("✅ 设置完成！")
        print("=" * 60)
        print()
        print("💡 下一步:")
        print("   运行测试: python scripts/test-ai-sql-execution.py")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
        return False
    finally:
        session.close()

if __name__ == "__main__":
    try:
        setup_tenant_and_datasource()
    except KeyboardInterrupt:
        print("\n\n⚠️  操作已取消")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()

