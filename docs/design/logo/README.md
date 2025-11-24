# DataAgent V4.1 Logo 设计与使用指南

## 概述

本文档介绍了 DataAgent V4.1 的官方logo设计、使用方法和MinIO上传配置。

## Logo文件

### 可用文件

1. **DataAgent_V4_1_Logo_Enhanced.svg** (推荐)
   - 路径: `docs/design/logo/DataAgent_V4_1_Logo_Enhanced.svg`
   - 格式: SVG矢量图
   - 特点: 完整渐变效果、3D质感、数据流动动画
   - 用途: 网页、文档、高分辨率场景

2. **logo.svg** (简化版)
   - 路径: `frontend/public/logo.svg`
   - 格式: SVG矢量图
   - 特点: 优化加载、适合前端直接使用
   - 用途: Next.js应用直接引用

### Logo设计元素

- **主色调**: 蓝色渐变 (#0EA5E9 → #3B82F6 → #6366F1)
- **辅助色**: 青色渐变 (#10B981 → #059669)
- **AI元素**: 紫色渐变 (#8B5CF6 → #6D28D9)
- **字体**: Arial, 加粗
- **尺寸**: 320×80px (可缩放)

## 使用方法

### 1. 前端应用中使用

```tsx
// Next.js组件中使用
import logo from '../public/logo.svg';

function Logo() {
  return (
    <img
      src={logo}
      alt="DataAgent V4.1 Logo"
      className="h-8 w-auto"
    />
  );
}
```

### 2. CSS背景使用

```css
.logo-container {
  background-image: url('/logo.svg');
  background-size: contain;
  background-repeat: no-repeat;
  background-position: center;
  width: 320px;
  height: 80px;
}
```

### 3. Markdown文档中使用

```markdown
![DataAgent V4.1 Logo](/logo.svg)
```

## MinIO上传配置

### 当前状态

Logo文件已准备好，但MinIO上传遇到认证问题。以下是解决方案：

### 方案1: 修复MinIO认证

1. **检查当前凭据**:
   ```bash
   docker exec dataagent-minio env | grep MINIO
   ```

2. **使用正确凭据**:
   - 从`.env`文件读取: `MINIO_ROOT_USER` 和 `MINIO_ROOT_PASSWORD`
   - 或使用MinIO控制台查看

3. **运行上传脚本**:
   ```bash
   cd scripts
   python simple_logo_upload.py
   ```

### 方案2: 使用MinIO控制台上传

1. **访问控制台**: http://localhost:9001
2. **登录**: 使用正确的凭据
3. **创建存储桶**: `dataagent-files`
4. **上传文件**: 将logo文件上传到 `assets/` 目录

### 方案3: 使用Web界面API

```javascript
// 前端直接上传到MinIO
const uploadLogo = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch('/api/upload/logo', {
    method: 'POST',
    body: formData
  });

  return response.json();
};
```

## MinIO环境变量配置

确保`.env`文件包含以下配置：

```bash
# MinIO对象存储配置
MINIO_ENDPOINT=localhost:9000
MINIO_ROOT_USER="your_root_user"
MINIO_ROOT_PASSWORD="your_root_password"
MINIO_ACCESS_KEY="your_access_key"
MINIO_SECRET_KEY="your_secret_key"
MINIO_SECURE=false
MINIO_BUCKET_NAME=dataagent-files
```

## 上传脚本使用

### 完整上传脚本

```bash
# 使用完整功能的上传脚本
cd scripts
python upload_assets.py --type logos
```

### 简化上传脚本

```bash
# 使用简化版上传脚本
cd scripts
python simple_logo_upload.py
```

### Windows批处理脚本

```batch
# Windows环境使用
cd scripts
upload_logos.bat
```

## Logo使用规范

### 尺寸建议

- **小尺寸**: 64×16px (favicon、小图标)
- **中等尺寸**: 160×40px (导航栏)
- **大尺寸**: 320×80px (页面标题、演示)
- **超大尺寸**: 640×160px (宣传材料)

### 颜色变体

1. **标准版**: 蓝色渐变主色调
2. **白色版**: 适用于深色背景
3. **黑色版**: 适用于浅色背景

### 使用场景

- ✅ 官网和产品页面
- ✅ 文档和演示材料
- ✅ 社交媒体和营销
- ❌ 修改Logo颜色或形状
- ❌ 添加第三方商标或元素

## 故障排除

### 常见问题

1. **MinIO认证失败**
   - 检查环境变量配置
   - 确认MinIO服务运行状态
   - 验证凭据正确性

2. **SVG文件不显示**
   - 检查文件路径
   - 确认MIME类型配置
   - 验证浏览器兼容性

3. **Logo变形或模糊**
   - 使用SVG格式保持清晰度
   - 设置正确的CSS尺寸
   - 避免过度缩放

### 调试命令

```bash
# 检查MinIO服务状态
docker ps | findstr minio

# 查看MinIO日志
docker logs dataagent-minio

# 测试MinIO连接
curl http://localhost:9000/minio/health/live
```

## 技术支持

如有问题，请参考：
- 项目文档: `docs/CLAUDE.md`
- MinIO官方文档: https://docs.min.io
- 前端开发指南: `frontend/CLAUDE.md`

---

**更新日期**: 2025-11-23
**版本**: V4.1
**维护者**: DataAgent开发团队