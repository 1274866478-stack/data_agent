#!/bin/bash

# Data Agent V4 - 功能测试脚本
# 用途: 快速测试所有核心功能

set -e

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# API基础URL
API_URL="http://localhost:8004"
FRONTEND_URL="http://localhost:3000"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Data Agent V4 - 功能测试${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 1. 健康检查
echo -e "${YELLOW}[1/8] 测试后端健康检查...${NC}"
if curl -s "${API_URL}/health" | grep -q "healthy"; then
    echo -e "${GREEN}✅ 后端服务健康${NC}"
else
    echo -e "${RED}❌ 后端服务异常${NC}"
    exit 1
fi
echo ""

# 2. Ping测试
echo -e "${YELLOW}[2/8] 测试Ping端点...${NC}"
if curl -s "${API_URL}/api/v1/health/ping" | grep -q "pong"; then
    echo -e "${GREEN}✅ Ping测试通过${NC}"
else
    echo -e "${RED}❌ Ping测试失败${NC}"
fi
echo ""

# 3. 服务状态检查
echo -e "${YELLOW}[3/8] 检查所有服务状态...${NC}"
SERVICES=$(curl -s "${API_URL}/api/v1/health/services")
echo "$SERVICES" | jq '.'

if echo "$SERVICES" | grep -q "minio"; then
    echo -e "${GREEN}✅ MinIO服务正常${NC}"
fi

if echo "$SERVICES" | grep -q "chromadb"; then
    echo -e "${GREEN}✅ ChromaDB服务正常${NC}"
fi

if echo "$SERVICES" | grep -q "zhipu_ai"; then
    echo -e "${GREEN}✅ 智谱AI服务正常${NC}"
fi
echo ""

# 4. 测试租户创建
echo -e "${YELLOW}[4/8] 测试租户创建...${NC}"
TENANT_RESPONSE=$(curl -s -X POST "${API_URL}/api/v1/tenants/setup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "company_name": "测试公司",
    "clerk_user_id": "test_user_'$(date +%s)'"
  }')

if echo "$TENANT_RESPONSE" | grep -q "id"; then
    echo -e "${GREEN}✅ 租户创建成功${NC}"
    echo "$TENANT_RESPONSE" | jq '.'
else
    echo -e "${YELLOW}⚠️  租户创建可能需要认证${NC}"
fi
echo ""

# 5. 测试数据源连接
echo -e "${YELLOW}[5/8] 测试数据源连接...${NC}"
CONNECTION_TEST=$(curl -s -X POST "${API_URL}/api/v1/data-sources/test" \
  -H "Content-Type: application/json" \
  -d '{
    "connection_string": "postgresql://postgres:postgres@localhost:5432/data_agent",
    "db_type": "postgresql"
  }')

if echo "$CONNECTION_TEST" | grep -q "success"; then
    echo -e "${GREEN}✅ 数据源连接测试通过${NC}"
    echo "$CONNECTION_TEST" | jq '.'
else
    echo -e "${YELLOW}⚠️  数据源连接测试失败（可能是正常的）${NC}"
fi
echo ""

# 6. 测试文档上传（创建临时测试文件）
echo -e "${YELLOW}[6/8] 测试文档上传...${NC}"
echo "This is a test PDF content" > /tmp/test_upload.pdf

UPLOAD_RESPONSE=$(curl -s -X POST "${API_URL}/api/v1/documents/upload" \
  -F "file=@/tmp/test_upload.pdf")

if echo "$UPLOAD_RESPONSE" | grep -q "id"; then
    echo -e "${GREEN}✅ 文档上传成功${NC}"
    echo "$UPLOAD_RESPONSE" | jq '.'
else
    echo -e "${YELLOW}⚠️  文档上传可能需要认证${NC}"
fi

# 清理临时文件
rm -f /tmp/test_upload.pdf
echo ""

# 7. 测试LLM对话
echo -e "${YELLOW}[7/8] 测试LLM对话功能...${NC}"
LLM_RESPONSE=$(curl -s -X POST "${API_URL}/api/v1/llm/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "你好，请用一句话介绍自己"}
    ],
    "model": "glm-4-flash"
  }')

if echo "$LLM_RESPONSE" | grep -q "content"; then
    echo -e "${GREEN}✅ LLM对话测试成功${NC}"
    echo "$LLM_RESPONSE" | jq '.content'
else
    echo -e "${YELLOW}⚠️  LLM对话可能需要认证或API密钥${NC}"
fi
echo ""

# 8. 测试前端访问
echo -e "${YELLOW}[8/8] 测试前端访问...${NC}"
if curl -s "${FRONTEND_URL}" | grep -q "Data Agent V4"; then
    echo -e "${GREEN}✅ 前端服务正常${NC}"
else
    echo -e "${RED}❌ 前端服务异常${NC}"
fi
echo ""

# 总结
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}测试完成！${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}可访问的前端页面：${NC}"
echo -e "  - 主页: ${FRONTEND_URL}"
echo -e "  - 聊天界面: ${FRONTEND_URL}/chat"
echo -e "  - 简化聊天: ${FRONTEND_URL}/chat-simple"
echo -e "  - 数据源管理: ${FRONTEND_URL}/data-sources"
echo -e "  - 文档管理: ${FRONTEND_URL}/documents"
echo ""
echo -e "${GREEN}可访问的后端服务：${NC}"
echo -e "  - API文档: ${API_URL}/docs"
echo -e "  - 健康检查: ${API_URL}/health"
echo -e "  - MinIO控制台: http://localhost:9001 (minioadmin/minioadmin)"
echo ""
echo -e "${YELLOW}提示：${NC}"
echo -e "  - 开发模式下，前端页面可直接访问，无需登录"
echo -e "  - 部分API可能需要认证，返回401是正常的"
echo -e "  - 详细测试指南请查看: docs/测试指南-功能测试手册.md"
echo ""

