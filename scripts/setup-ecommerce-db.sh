#!/bin/bash
# ================================================================
# 电商测试数据库快速初始化脚本 (Linux/Mac)
# ================================================================

set -e

echo "========================================"
echo "电商测试数据库初始化工具"
echo "========================================"
echo ""

# 设置数据库连接参数
PGHOST=${PGHOST:-localhost}
PGPORT=${PGPORT:-5432}
PGUSER=${PGUSER:-dev}
PGPASSWORD=${PGPASSWORD:-dev123}
PGDATABASE=${PGDATABASE:-postgres}
NEW_DB=ecommerce_test_db

export PGPASSWORD

echo "[1/4] 检查PostgreSQL连接..."
if ! psql -h $PGHOST -p $PGPORT -U $PGUSER -d $PGDATABASE -c "SELECT version();" > /dev/null 2>&1; then
    echo "❌ 无法连接到PostgreSQL，请检查："
    echo "   - PostgreSQL服务是否运行"
    echo "   - 连接参数是否正确 (主机: $PGHOST, 端口: $PGPORT, 用户: $PGUSER)"
    exit 1
fi
echo "✅ PostgreSQL连接成功"

echo ""
echo "[2/4] 检查数据库是否存在..."
if psql -h $PGHOST -p $PGPORT -U $PGUSER -d $PGDATABASE -tAc "SELECT 1 FROM pg_database WHERE datname='$NEW_DB'" | grep -q 1; then
    echo "⚠️  数据库 $NEW_DB 已存在"
    read -p "是否删除并重新创建? (y/N): " CONFIRM
    if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
        echo "取消操作"
        exit 0
    fi
    echo "正在删除旧数据库..."
    psql -h $PGHOST -p $PGPORT -U $PGUSER -d $PGDATABASE -c "DROP DATABASE IF EXISTS $NEW_DB;"
fi

echo ""
echo "[3/4] 创建新数据库..."
psql -h $PGHOST -p $PGPORT -U $PGUSER -d $PGDATABASE -c "CREATE DATABASE $NEW_DB;"
echo "✅ 数据库创建成功"

echo ""
echo "[4/4] 初始化数据..."
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
psql -h $PGHOST -p $PGPORT -U $PGUSER -d $NEW_DB -f "$SCRIPT_DIR/init-ecommerce-test-db.sql"

echo ""
echo "========================================"
echo "✅ 电商测试数据库初始化完成！"
echo "========================================"
echo ""
echo "数据库信息:"
echo "  - 数据库名: $NEW_DB"
echo "  - 主机: $PGHOST"
echo "  - 端口: $PGPORT"
echo "  - 用户: $PGUSER"
echo ""
echo "连接字符串:"
echo "  postgresql://$PGUSER:$PGPASSWORD@$PGHOST:$PGPORT/$NEW_DB"
echo ""
echo "数据统计:"
psql -h $PGHOST -p $PGPORT -U $PGUSER -d $NEW_DB -c "SELECT (SELECT COUNT(*) FROM users) as users, (SELECT COUNT(*) FROM products) as products, (SELECT COUNT(*) FROM orders) as orders, (SELECT COUNT(*) FROM reviews) as reviews;"
echo ""
echo "下一步:"
echo "  1. 在Data Agent中添加此数据源"
echo "  2. 使用AI助手测试数据查询"
echo "  3. 查看 电商测试数据库使用指南.md 了解更多示例"
echo ""

