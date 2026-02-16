#!/usr/bin/env python3
"""
更新 docker-compose.yml 中的路径引用
"""

import re
from pathlib import Path

# docker-compose.yml 路径
docker_compose_path = Path(__file__).parent.parent.parent / "config" / "docker-compose.yml"

# 路径替换映射
PATH_REPLACEMENTS = {
    "./frontend": "../apps/frontend",
    "./backend": "../apps/backend",
    "./Agent": "../services/agent-v1",
    "./AgentV2": "../services/agent-v2",
    "./scripts": "../tools/deployment",
    "./data_storage": "../infrastructure/storage/data_storage",
    "./backend/migrations": "../infrastructure/database/migrations",
    "./backend/scripts": "../apps/backend/scripts",
    ".env": "../.env",
}

def update_docker_compose():
    """更新 docker-compose.yml 文件"""

    with open(docker_compose_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # 更新 context 路径
    content = re.sub(
        r'context:\s+\.\/frontend',
        'context: ../apps/frontend',
        content
    )

    content = re.sub(
        r'context:\s+\.\/backend',
        'context: ../apps/backend',
        content
    )

    # 更新 volume 挂载路径
    content = re.sub(
        r'\-\s+\.\/frontend:',
        r'- ../apps/frontend:',
        content
    )

    content = re.sub(
        r'\-\s+\.\/backend:',
        r'- ../apps/backend:',
        content
    )

    content = re.sub(
        r'\-\s+\.\/Agent:',
        r'- ../services/agent-v1:',
        content
    )

    content = re.sub(
        r'\-\s+\.\/AgentV2:',
        r'- ../services/agent-v2:',
        content
    )

    content = re.sub(
        r'\-\s+\.\/data_storage:',
        r'- ../infrastructure/storage/data_storage:',
        content
    )

    content = re.sub(
        r'\-\s+\.\/scripts:',
        r'- ../tools/deployment:',
        content
    )

    content = re.sub(
        r'\-\s+\.\/backend\/migrations:',
        r'- ../infrastructure/database/migrations:',
        content
    )

    content = re.sub(
        r'\-\s+\.\/backend\/scripts:',
        r'- ../apps/backend/scripts:',
        content
    )

    # 更新 env_file 路径
    content = re.sub(
        r'env_file:\s*\n\s+\-\.env',
        'env_file:\n      - ../.env',
        content
    )

    if content != original_content:
        with open(docker_compose_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Updated docker-compose.yml")
    else:
        print("No changes needed in docker-compose.yml")

if __name__ == "__main__":
    update_docker_compose()
