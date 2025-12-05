"""
创建测试数据库并导入Excel数据
使用 ecommerce_test_data.xlsx 中的电商测试数据
"""
import pandas as pd
from sqlalchemy import create_engine, text
import sys
import os

# 数据库配置
DB_USER = "postgres"
DB_PASSWORD = "password"  # 请根据你的实际密码修改
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "test_ecommerce"

# Excel文件路径
EXCEL_PATH = os.path.join(os.path.dirname(__file__), "..", "scripts", "ecommerce_test_data.xlsx")


def create_database():
    """创建数据库（如果不存在）"""
    # 连接到默认的 postgres 数据库
    engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/postgres")
    
    with engine.connect() as conn:
        # 需要在自动提交模式下创建数据库
        conn.execute(text("COMMIT"))
        
        # 检查数据库是否存在
        result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'"))
        exists = result.fetchone() is not None
        
        if not exists:
            conn.execute(text(f"CREATE DATABASE {DB_NAME}"))
            print(f"✅ 数据库 '{DB_NAME}' 创建成功")
        else:
            print(f"ℹ️  数据库 '{DB_NAME}' 已存在")
    
    engine.dispose()


def import_excel_data():
    """从Excel导入数据到数据库"""
    # 连接到测试数据库
    engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    
    # 读取Excel文件
    xl = pd.ExcelFile(EXCEL_PATH)
    
    # Sheet名称到表名的映射
    sheet_to_table = {
        "用户表": "users",
        "商品表": "products", 
        "分类表": "categories",
        "订单表": "orders",
        "订单明细": "order_items",
        "评价表": "reviews",
        "地址表": "addresses"
    }
    
    print(f"\n📊 开始导入数据...")
    
    for sheet_name, table_name in sheet_to_table.items():
        df = pd.read_excel(xl, sheet_name)
        
        # 将数据写入数据库
        df.to_sql(table_name, engine, if_exists='replace', index=False)
        print(f"  ✅ {sheet_name} -> {table_name} ({len(df)} 行)")
    
    engine.dispose()
    print(f"\n✅ 所有数据导入完成!")


def verify_data():
    """验证导入的数据"""
    engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    
    print(f"\n📋 数据验证:")
    
    tables = ["users", "products", "categories", "orders", "order_items", "reviews", "addresses"]
    
    with engine.connect() as conn:
        for table in tables:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.fetchone()[0]
            print(f"  📌 {table}: {count} 行")
    
    engine.dispose()


def update_env_file():
    """更新.env文件中的数据库连接"""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    db_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    # 读取现有内容
    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换DATABASE_URL
    import re
    new_content = re.sub(
        r'DATABASE_URL=.*',
        f'DATABASE_URL={db_url}',
        content
    )
    
    # 写回文件
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"\n✅ 已更新 .env 文件中的 DATABASE_URL")
    print(f"   {db_url}")


if __name__ == "__main__":
    print("="*60)
    print("🚀 测试数据库设置脚本")
    print("="*60)
    
    try:
        # 1. 创建数据库
        create_database()
        
        # 2. 导入Excel数据
        import_excel_data()
        
        # 3. 验证数据
        verify_data()
        
        # 4. 更新.env文件
        update_env_file()
        
        print("\n" + "="*60)
        print("🎉 设置完成! 现在可以运行 python sql_agent.py 测试")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)

