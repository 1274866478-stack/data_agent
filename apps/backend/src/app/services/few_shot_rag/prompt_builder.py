"""
Prompt Builder - 动态少样本 Prompt 构建

负责：
1. 从 Qdrant 检索相似案例
2. 构建 Few-Shot Prompt
3. 动态调整示例数量
"""

import os
from typing import List, Dict, Any, Optional
from openai import OpenAI

from backend.src.app.core.config import settings
from .qdrant_service import QdrantService


class PromptBuilder:
    """动态 Prompt 构建器"""

    def __init__(self):
        self.qdrant_service = QdrantService()
        self.embedding_client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    async def _get_embedding(self, text: str) -> List[float]:
        """获取文本向量"""
        if not self.embedding_client:
            # 使用备用方案（简单哈希）
            import hashlib
            hash_obj = hashlib.md5(text.encode())
            # 将哈希转换为向量
            return [float(ord(c)) / 255.0 for c in hash_obj.hexdigest()[:1536]]

        try:
            response = self.embedding_client.embeddings.create(
                model=settings.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"获取 embedding 失败: {e}")
            # 返回零向量
            return [0.0] * settings.embedding_dimension

    async def build_prompt_with_examples(
        self,
        tenant_id: str,
        query: str,
        cube_schema: Dict[str, Any],
        max_examples: int = 3,
        filters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        构建包含相似示例的 Prompt

        Args:
            tenant_id: 租户 ID
            query: 用户查询
            cube_schema: Cube 定义
            max_examples: 最大示例数量
            filters: 额外过滤条件

        Returns:
            增强后的 Prompt
        """
        # 1. 获取查询向量
        query_embedding = await self._get_embedding(query)

        # 2. 检索相似案例
        similar_queries = await self.qdrant_service.find_similar_queries(
            tenant_id=tenant_id,
            question_embedding=query_embedding,
            top_k=max_examples,
            filters=filters
        )

        # 3. 构建 Few-Shot Prompt
        prompt = self._build_base_prompt(cube_schema)

        if similar_queries:
            prompt += "\n\n## 参考示例\n\n"
            for i, example in enumerate(similar_queries, 1):
                prompt += f"### 示例 {i}\n"
                prompt += f"**用户问题**: {example['question']}\n"
                prompt += f"**DSL JSON**: {example['metadata'].get('dsl_json', {})}\n"
                if example['metadata'].get('success'):
                    prompt += f"**结果**: 成功\n"
                prompt += "\n"

        # 4. 添加当前查询
        prompt += "\n## 当前查询\n\n"
        prompt += f"**用户问题**: {query}\n"
        prompt += "**请生成对应的 DSL JSON**:\n"

        return prompt

    def _build_base_prompt(self, cube_schema: Dict[str, Any]) -> str:
        """构建基础 Prompt"""
        prompt = """# ChatBI DSL 生成器

你是一个专业的数据查询 DSL 生成器。根据用户问题和语义层定义，生成 Cube.js DSL JSON。

## DSL 格式说明

```json
{
  "cube": "Cube名称",
  "measures": ["度量列表"],
  "dimensions": ["维度列表"],
  "timeDimension": "时间维度",
  "granularity": ["时间粒度"],
  "filters": [
    {
      "member": "字段名",
      "operator": "操作符",
      "values": ["值列表"]
    }
  ],
  "order": [
    {
      "member": "字段名",
      "direction": "asc|desc"
    }
  ],
  "limit": 数字
}
```

## 可用语义层定义

"""
        # 添加 Cube 定义
        for cube_name, cube_def in cube_schema.items():
            prompt += f"\n### {cube_name}\n"
            prompt += f"- 度量: {', '.join(cube_def.get('measures', []))}\n"
            prompt += f"- 维度: {', '.join(cube_def.get('dimensions', []))}\n"

        prompt += """

## 生成规则

1. **度量选择**: 根据问题中的关键词选择合适的度量（如"销售额"→total_revenue）
2. **维度选择**: 选择相关的分组维度
3. **时间处理**: 包含时间关键词时使用 timeDimension 和 granularity
4. **过滤条件**: 根据问题中的条件添加 filters
5. **排序**: 按"最/前/后"等关键词排序
6. **限制**: 默认使用 limit=100 避免数据过多

"""
        return prompt

    async def store_successful_query(
        self,
        tenant_id: str,
        query_id: str,
        question: str,
        dsl_json: Dict[str, Any],
        cube_name: str,
        execution_time_ms: int,
        success: bool = True,
        user_rating: Optional[int] = None
    ):
        """存储成功查询到向量库"""
        # 只存储高质量查询
        if user_rating and user_rating < 4:
            return

        embedding = await self._get_embedding(question)

        metadata = {
            "dsl_json": dsl_json,
            "cube_name": cube_name,
            "execution_time_ms": execution_time_ms,
            "success": success,
            "user_rating": user_rating
        }

        await self.qdrant_service.store_query(
            tenant_id=tenant_id,
            query_id=query_id,
            question=question,
            embedding=embedding,
            metadata=metadata
        )
