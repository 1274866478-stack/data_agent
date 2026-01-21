"""
ChromaDB → Qdrant 迁移脚本

将 ChromaDB 中的向量数据迁移到 Qdrant
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any
import asyncio

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
import chromadb
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct


class ChromaToQdrantMigrator:
    """ChromaDB 到 Qdrant 的迁移器"""

    def __init__(self, chroma_host: str = "localhost", chroma_port: int = 8001,
                 qdrant_host: str = "localhost", qdrant_port: int = 6333):
        self.chroma_client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
        self.qdrant_client = QdrantClient(host=qdrant_host, port=qdrant_port)

    async def list_chroma_collections(self) -> List[str]:
        """列出 ChromaDB 中的所有集合"""
        collections = self.chroma_client.list_collections()
        return [c.name for c in collections]

    async def migrate_collection(
        self,
        collection_name: str,
        tenant_id: str = "default",
        batch_size: int = 100,
        verify: bool = False
    ) -> Dict[str, Any]:
        """
        迁移单个集合

        Args:
            collection_name: ChromaDB 集合名称
            tenant_id: 租户 ID
            batch_size: 批次大小
            verify: 是否验证迁移结果

        Returns:
            迁移结果统计
        """
        print(f"\n开始迁移集合: {collection_name}")

        # 获取 ChromaDB 集合
        try:
            chroma_collection = self.chroma_client.get_collection(collection_name)
        except Exception as e:
            print(f"  ✗ 集合不存在: {e}")
            return {"success": False, "error": str(e)}

        # 获取集合中的数据
        count = chroma_collection.count()
        print(f"  原始数据量: {count} 条")

        if count == 0:
            print(f"  ⊙ 集合为空，跳过迁移")
            return {"success": True, "migrated_count": 0}

        # 创建 Qdrant 集合
        qdrant_collection_name = f"dataagent_{tenant_id}_{collection_name}"

        # 检查向量维度
        sample = chroma_collection.get(limit=1, include=["embeddings"])
        if not sample["embeddings"]:
            print(f"  ✗ 无法获取向量维度")
            return {"success": False, "error": "无法获取向量维度"}

        vector_size = len(sample["embeddings"][0])
        print(f"  向量维度: {vector_size}")

        # 创建 Qdrant 集合（如果不存在）
        collections = self.qdrant_client.get_collections().collections
        collection_names = [c.name for c in collections]

        if qdrant_collection_name not in collection_names:
            self.qdrant_client.create_collection(
                collection_name=qdrant_collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
            )
            print(f"  ✓ 创建 Qdrant 集合: {qdrant_collection_name}")
        else:
            print(f"  ⊙ Qdrant 集合已存在")

        # 分批迁移数据
        migrated_count = 0
        offset = 0

        while offset < count:
            # 从 ChromaDB 获取数据
            batch = chroma_collection.get(
                limit=batch_size,
                offset=offset,
                include=["embeddings", "metadatas", "documents"]
            )

            if not batch["ids"]:
                break

            # 构建 Qdrant points
            points = []
            for i, doc_id in enumerate(batch["ids"]):
                # 提取 tenant_id (假设在 metadata 中)
                metadata = batch["metadatas"][i] or {}
                item_tenant_id = metadata.get("tenant_id", tenant_id)

                point_id = f"{item_tenant_id}_{collection_name}_{doc_id}"

                points.append(PointStruct(
                    id=point_id,
                    vector=batch["embeddings"][i],
                    payload={
                        "document": batch["documents"][i] if batch["documents"] else "",
                        "metadata": metadata,
                        "original_id": str(doc_id),
                        "collection": collection_name
                    }
                ))

            # 上传到 Qdrant
            self.qdrant_client.upsert(
                collection_name=qdrant_collection_name,
                points=points
            )

            batch_count = len(points)
            migrated_count += batch_count
            offset += batch_size

            print(f"  进度: {migrated_count}/{count} ({migrated_count*100//count}%)")

        print(f"  ✓ 迁移完成: {migrated_count} 条")

        # 验证迁移结果
        if verify:
            qdrant_count = self.qdrant_client.count_records(qdrant_collection_name)
            if qdrant_count == migrated_count:
                print(f"  ✓ 验证通过: Qdrant 中有 {qdrant_count} 条记录")
            else:
                print(f"  ✗ 验证失败: Qdrant 中有 {qdrant_count} 条记录，预期 {migrated_count}")

        return {
            "success": True,
            "original_count": count,
            "migrated_count": migrated_count,
            "qdrant_collection": qdrant_collection_name
        }

    async def migrate_all(
        self,
        tenant_id: str = "default",
        batch_size: int = 100,
        verify: bool = True,
        skip_collections: List[str] = None
    ) -> Dict[str, Any]:
        """
        迁移所有集合

        Args:
            tenant_id: 租户 ID
            batch_size: 批次大小
            verify: 是否验证迁移结果
            skip_collections: 要跳过的集合列表

        Returns:
            迁移结果统计
        """
        skip_collections = skip_collections or []

        # 获取所有集合
        collections = await self.list_chroma_collections()

        if not collections:
            print("没有找到任何集合")
            return {"success": True, "collections": []}

        print(f"找到 {len(collections)} 个集合: {collections}")

        results = []
        total_migrated = 0

        for collection_name in collections:
            if collection_name in skip_collections:
                print(f"\n跳过集合: {collection_name}")
                continue

            result = await self.migrate_collection(
                collection_name=collection_name,
                tenant_id=tenant_id,
                batch_size=batch_size,
                verify=verify
            )

            results.append({
                "collection": collection_name,
                "result": result
            })

            if result.get("success"):
                total_migrated += result.get("migrated_count", 0)

        return {
            "success": True,
            "total_collections": len(collections),
            "migrated_collections": len([r for r in results if r["result"].get("success")]),
            "total_migrated": total_migrated,
            "collections": results
        }


async def main():
    """主函数"""
    load_dotenv()

    # 从环境变量读取配置
    chroma_host = os.getenv("CHROMA_HOST", "localhost")
    chroma_port = int(os.getenv("CHROMA_PORT", "8001"))
    qdrant_host = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))

    print("=" * 60)
    print("ChromaDB → Qdrant 迁移工具")
    print("=" * 60)
    print(f"ChromaDB: {chroma_host}:{chroma_port}")
    print(f"Qdrant:  {qdrant_host}:{qdrant_port}")
    print("=" * 60)

    # 创建迁移器
    migrator = ChromaToQdrantMigrator(
        chroma_host=chroma_host,
        chroma_port=chroma_port,
        qdrant_host=qdrant_host,
        qdrant_port=qdrant_port
    )

    # 执行迁移
    result = await migrator.migrate_all(
        tenant_id="default",
        batch_size=100,
        verify=True
    )

    # 输出结果
    print("\n" + "=" * 60)
    print("迁移完成!")
    print("=" * 60)
    print(f"总集合数: {result['total_collections']}")
    print(f"已迁移: {result['migrated_collections']}")
    print(f"总记录数: {result['total_migrated']}")
    print("=" * 60)

    # 详细结果
    for item in result.get("collections", []):
        status = "✓" if item["result"].get("success") else "✗"
        count = item["result"].get("migrated_count", 0)
        print(f"{status} {item['collection']}: {count} 条")


if __name__ == "__main__":
    asyncio.run(main())
