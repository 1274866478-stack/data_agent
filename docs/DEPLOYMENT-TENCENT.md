# 腾讯云部署指南

## 服务器信息

| 项目 | 值 |
|------|-----|
| IP | 101.35.226.59 |
| 用户 | ubuntu |
| 域名 | bichat.matrix-ai.com.cn |
| 项目目录 | /opt/bichat |
| 数据目录 | /opt/bichat_data |

## 端口配置

| 服务 | 容器端口 | 宿主机端口 | 说明 |
|------|----------|------------|------|
| Frontend | 3000 | 3002 | Next.js 应用 |
| Backend | 8000 | 8002 | FastAPI 服务 |
| PostgreSQL | 5432 | - | 内网访问 |
| MinIO | 9000/9001 | - | 内网访问 |
| Qdrant | 6333/6334 | - | 内网访问 |

## 快速部署

### 本地操作

```bash
# 1. 打包项目
bash scripts/package-for-deploy.sh

# 2. 上传到服务器
bash scripts/upload-to-server.sh
```

### 服务器操作

```bash
# 1. SSH 登录
ssh ubuntu@101.35.226.59

# 2. 解压部署包
cd /opt
sudo mkdir -p bichat
sudo tar -xzf ~/insight-agent-deploy.tar.gz -C /opt/
sudo mv insight-agent-deploy/* bichat/
sudo mv insight-agent-deploy/.* bichat/ 2>/dev/null || true
sudo rmdir insight-agent-deploy

# 3. 执行部署脚本
cd /opt/bichat
sudo bash scripts/deploy-on-server.sh

# 4. 验证容器状态
docker ps | grep bichat
```

## Nginx 配置

### 上传 Nginx 配置

```bash
# 在本地执行
scp nginx/bichat.matrix-ai.com.cn.conf ubuntu@101.35.226.59:/tmp/

# 在服务器上执行
sudo mv /tmp/bichat.matrix-ai.com.cn.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/bichat.matrix-ai.com.cn.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 获取 SSL 证书

```bash
# 安装 certbot (如未安装)
sudo apt update
sudo apt install certbot python3-certbot-nginx -y

# 获取证书
sudo certbot --nginx -d bichat.matrix-ai.com.cn
```

## 验证部署

```bash
# 检查容器状态
docker ps | grep bichat

# 检查日志
docker logs bichat-frontend --tail 20
docker logs bichat-backend --tail 20

# 测试访问
curl http://localhost:3002
curl http://localhost:8002/api/v1/health
curl https://bichat.matrix-ai.com.cn
```

## 故障排查

### 容器启动失败

```bash
# 查看详细日志
docker-compose -f docker-compose.tencent.yml logs

# 重启特定服务
docker-compose -f docker-compose.tencent.yml restart backend
```

### 网络问题

```bash
# 检查网络
docker network ls | grep bichat

# 重建网络
docker network rm bichat-network
docker network create bichat-network
```

### 端口冲突

```bash
# 检查端口占用
sudo netstat -tulpn | grep :3002
sudo netstat -tulpn | grep :8002
```

## 常用命令

```bash
# 启动所有服务
docker-compose -f docker-compose.tencent.yml up -d

# 停止所有服务
docker-compose -f docker-compose.tencent.yml down

# 查看日志
docker-compose -f docker-compose.tencent.yml logs -f

# 重启服务
docker-compose -f docker-compose.tencent.yml restart backend
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `scripts/package-for-deploy.sh` | 本地打包脚本 |
| `scripts/upload-to-server.sh` | 上传脚本 |
| `scripts/deploy-on-server.sh` | 服务器部署脚本 |
| `docker-compose.tencent.yml` | 腾讯云专用配置 |
| `.env.tencent` | 生产环境变量模板 |
| `nginx/bichat.matrix-ai.com.cn.conf` | Nginx 站点配置 |
