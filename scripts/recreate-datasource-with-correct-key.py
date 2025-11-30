#!/usr/bin/env python3
"""
使用正确的加密密钥重新创建数据源
"""

import sys
import os

# 添加backend到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

# 设置环境变量（必须在导入之前）
os.environ['ENCRYPTION_KEY'] = 'V1ZvT09XWm5MWDl4aHNwamIwOFUwX0ZSdlNfclNTVnUxMmM5cTViaVVOdz0='

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.app.data.models import DataSourceConnection, DataSourceConnectionStatus
from src.app.services.encryption_service import encryption_service
import uuid
from datetime import datetime

# 数据库连接
DATABASE_URL = "postgresql://postgres:password@localhost:5432/dataagent"

def recreate_datasource():
    """重新创建数据源"""
    print("=" * 60)
    print("  重新创建数据源（使用正确的加密密钥）")
    print("=" * 60)
    print()
    
    # 创建数据库引擎
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        tenant_id = "default_tenant"
        datasource_name = "ChatBI测试数据库"
        
        # 1. 删除旧的数据源
        print("🗑️  删除旧的数据源...")
        deleted_count = session.query(DataSourceConnection).filter(
            DataSourceConnection.tenant_id == tenant_id,
            DataSourceConnection.name == datasource_name
        ).delete()
        session.commit()
        print(f"✅ 已删除 {deleted_count} 个旧数据源")
        print()
        
        # 2. 创建新的数据源
        print(f"📝 创建新数据源: {datasource_name}")
        
        # 连接字符串（使用Docker网络内的主机名）
        connection_string = "postgresql://postgres:password@db:5432/chatbi_test"
        
        # 使用正确的密钥加密连接字符串
        print(f"🔐 使用加密密钥: {os.environ['ENCRYPTION_KEY'][:20]}...")
        encrypted_string = encryption_service.encrypt_connection_string(connection_string)
        print(f"✅ 连接字符串已加密")
        
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
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        session.add(datasource)
        session.commit()
        
        print("✅ 数据源创建成功")
        print(f"   ID: {datasource.id}")
        print(f"   类型: {datasource.db_type}")
        print(f"   数据库: {datasource.database_name}")
        print(f"   状态: {datasource.status}")
        print()
        
        # 3. 测试解密
        print("🔍 测试解密...")
        decrypted = encryption_service.decrypt_connection_string(encrypted_string)
        if decrypted == connection_string:
            print("✅ 解密测试成功！")
        else:
            print("❌ 解密测试失败！")
            print(f"   原始: {connection_string}")
            print(f"   解密: {decrypted}")
        
        print()
        print("=" * 60)
        print("✅ 完成！")
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
        recreate_datasource()
    except KeyboardInterrupt:
        print("\n\n⚠️  操作已取消")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()

