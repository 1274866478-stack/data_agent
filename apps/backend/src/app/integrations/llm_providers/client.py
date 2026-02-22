# llm_providers client 已删除
# 所有 ZhipuAI 相关功能现在直接从 zhipu_client.py 导入
# 保留此文件以维持向后兼容性
from src.app.integrations.llm_providers.zhipu_client import zhipu_service

__all__ = ["zhipu_service"]
