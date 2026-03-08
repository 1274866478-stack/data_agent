#!/bin/bash
# Deploy self-hosted auth to Tencent Cloud server

SERVER="ubuntu@101.35.226.59"
PROJECT_DIR="/opt/bichat"
DOMAIN="bichat.matrix-ai.com.cn"

echo "=== Deploying Self-Hosted Auth ==="
echo "Server: $SERVER"
echo "Domain: $DOMAIN"
echo ""

# 1. Pull latest code
echo "[1/5] Pulling latest code..."
ssh $SERVER "cd $PROJECT_DIR && git pull origin master"

# 2. Configure environment for self-host mode
echo "[2/5] Configuring self-host mode..."
ssh $SERVER "cd $PROJECT_DIR && \
  echo 'AUTH_MODE=selfhost' >> backend/.env && \
  echo 'NEXT_PUBLIC_AUTH_MODE=selfhost' >> frontend/.env.local"

# 3. Run database migration
echo "[3/5] Running database migration..."
ssh $SERVER "cd $PROJECT_DIR && docker-compose exec backend alembic upgrade head"

# 4. Restart services
echo "[4/5] Restarting services..."
ssh $SERVER "cd $PROJECT_DIR && docker-compose up -d backend frontend"

# 5. Check status
echo "[5/5] Checking service status..."
ssh $SERVER "cd $PROJECT_DIR && docker-compose ps"

echo ""
echo "=== Deployment Complete ==="
echo "Frontend: https://$DOMAIN"
echo "Backend API: https://$DOMAIN/api/v1"
echo "Register: https://$DOMAIN/register"
echo "Login: https://$DOMAIN/login"
