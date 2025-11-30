# 数据源上传功能修复文档

## 问题描述

用户报告在使用"数据库连接"标签页上传数据库连接时，遇到 **"Method Not Allowed"** 错误。

### 错误截图分析
- 错误信息: "Method Not Allowed"
- 发生位置: 数据源创建页面的"数据库连接"标签页
- 影响功能: 无法通过数据库连接字符串创建数据源

## 根本原因

### 1. 路由配置问题
在 `backend/src/app/api/v1/endpoints/data_sources.py` 文件中，`POST /data-sources/upload` 端点的 `tenant_id` 参数没有正确地从请求中获取。

**问题代码:**
```python
@router.post("/upload", summary="上传数据文件创建数据源", status_code=status.HTTP_201_CREATED)
async def upload_data_source(
    file: UploadFile = File(..., description="数据文件 (CSV, Excel, SQLite)"),
    name: str = Form(..., description="数据源名称"),
    db_type: Optional[str] = Form(None, description="数据类型"),
    tenant_id: str = None,  # ❌ 没有从查询参数中获取
    db: Session = Depends(get_db)
):
```

### 2. 前端调用方式
前端通过查询参数传递 `tenant_id`:
```typescript
const url = `${this.baseURL}/data-sources/upload?tenant_id=${tenantId}`
```

但后端没有正确提取这个查询参数。

## 修复方案

### 修改内容
在 `backend/src/app/api/v1/endpoints/data_sources.py` 第167-188行:

**修复后的代码:**
```python
@router.post("/upload", summary="上传数据文件创建数据源", status_code=status.HTTP_201_CREATED)
async def upload_data_source(
    file: UploadFile = File(..., description="数据文件 (CSV, Excel, SQLite)"),
    name: str = Form(..., description="数据源名称"),
    db_type: Optional[str] = Form(None, description="数据类型"),
    tenant_id: Optional[str] = None,  # ✅ 改为Optional
    request: Request = None,           # ✅ 添加Request参数
    db: Session = Depends(get_db)
):
    """
    上传数据文件创建数据源
    支持 CSV、Excel (.xls/.xlsx) 和 SQLite 数据库 (.db/.sqlite/.sqlite3) 文件
    """
    # ✅ 从查询参数获取tenant_id
    if not tenant_id and request:
        tenant_id = request.query_params.get("tenant_id")
    
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id is required"
        )
```

### 关键改动
1. **添加 `Request` 参数**: 允许访问查询参数
2. **从查询参数提取 `tenant_id`**: 使用 `request.query_params.get("tenant_id")`
3. **保持向后兼容**: 如果 `tenant_id` 已经通过其他方式提供，则不覆盖

## 测试验证

### 测试场景
1. **数据库连接创建** (POST /data-sources)
   - 应该正常工作 ✅
   
2. **文件上传创建数据源** (POST /data-sources/upload)
   - 之前失败 ❌
   - 修复后应该成功 ✅

### 测试脚本
运行 `test_upload_fix.py` 进行验证:
```bash
python test_upload_fix.py
```

## 影响范围

### 受影响的功能
- ✅ **文件上传数据源**: CSV、Excel、SQLite文件上传
- ✅ **数据库连接**: PostgreSQL连接字符串创建

### 不受影响的功能
- 数据源列表查询
- 数据源详情查询
- 数据源更新
- 数据源删除
- 连接测试

## 后续建议

### 1. 统一认证方式
建议在所有端点中使用统一的认证中间件，而不是手动从查询参数获取 `tenant_id`:

```python
from src.app.middleware.tenant_context import get_current_tenant_from_request

@router.post("/upload")
async def upload_data_source(
    file: UploadFile = File(...),
    name: str = Form(...),
    tenant: Tenant = Depends(get_current_tenant_from_request),  # 推荐方式
    db: Session = Depends(get_db)
):
    tenant_id = tenant.id
    # ...
```

### 2. 添加集成测试
为文件上传功能添加完整的集成测试，确保不会再次出现类似问题。

### 3. API文档更新
更新Swagger/OpenAPI文档，明确说明 `tenant_id` 的传递方式。

## 版本信息
- **修复日期**: 2025-11-30
- **修复版本**: V4.1
- **修复文件**: `backend/src/app/api/v1/endpoints/data_sources.py`
- **修复行数**: 167-188

## 相关文件
- `backend/src/app/api/v1/endpoints/data_sources.py` - 后端API端点
- `frontend/src/store/dataSourceStore.ts` - 前端数据源Store
- `frontend/src/components/data-sources/DataSourceForm.tsx` - 前端表单组件

