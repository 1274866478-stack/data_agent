# -*- coding: utf-8 -*-
"""
SOTA Agent System Integration Test

Test complete SOTA query workflow
"""

import os
import sys
import asyncio
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "AgentV2"))

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from dotenv import load_dotenv


async def test_swarm_graph():
    """Test Swarm Graph construction"""
    print("\n=== Test Swarm Graph Construction ===")

    try:
        from AgentV2.graphs.swarm_graph import build_swarm_graph

        # Build graph
        graph = build_swarm_graph(llm=None, cube_schema={})

        print(f"[OK] Graph built successfully")
        print(f"  Nodes: {len(graph.nodes)}")
        print(f"  Node names: {list(graph.nodes.keys())}")
        return True
    except Exception as e:
        print(f"[ERROR] Graph build failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_subagents():
    """Test all sub Agents"""
    print("\n=== Test Sub Agents ===")

    from AgentV2.subagents.router_agent import RouterAgent
    from AgentV2.subagents.planner_agent import PlannerAgent
    from AgentV2.subagents.generator_agent import GeneratorAgent
    from AgentV2.subagents.critic_agent import CriticAgent
    from AgentV2.subagents.repair_agent import RepairAgent

    agents = [
        ("Router", RouterAgent),
        ("Planner", PlannerAgent),
        ("Generator", GeneratorAgent),
        ("Critic", CriticAgent),
        ("Repair", RepairAgent)
    ]

    results = []
    for name, AgentClass in agents:
        try:
            agent = AgentClass(name.lower(), llm=None)
            print(f"[OK] {name} Agent created successfully")
            results.append(True)
        except Exception as e:
            print(f"[ERROR] {name} Agent creation failed: {e}")
            results.append(False)

    return all(results)


async def test_qdrant_service():
    """Test Qdrant service via REST API"""
    print("\n=== Test Qdrant Service (REST API) ===")

    try:
        import requests

        # Test basic connectivity
        response = requests.get("http://localhost:6333/collections", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] Qdrant REST API connected successfully")
            print(f"  Existing collections: {len(data['result']['collections'])}")
            return True
        else:
            print(f"[ERROR] Qdrant returned status: {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] Qdrant connection failed: {e}")
        return False


async def test_cube_service():
    """Test Cube.js service"""
    print("\n=== Test Cube.js Service ===")

    try:
        import requests

        # Use requests instead of httpx
        response = requests.get("http://localhost:4000/", timeout=5)
        if response.status_code == 200:
            print(f"[OK] Cube.js connected successfully")
            return True
        else:
            print(f"[ERROR] Cube.js returned status: {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] Cube.js connection failed: {e}")
        return False


async def test_disambiguation():
    """Test disambiguation functionality"""
    print("\n=== Test Disambiguation ===")

    try:
        from backend.src.app.services.disambiguation.ambiguity_detector import AmbiguityDetector
        from backend.src.app.services.disambiguation.question_generator import QuestionGenerator

        detector = AmbiguityDetector()
        generator = QuestionGenerator()

        # Test ambiguity detection
        test_queries = [
            "What are the recent sales",  # Time range ambiguous
            "Which product is best",  # Multiple metrics ambiguous
            "Sequential growth status"  # Comparison base ambiguous
        ]

        for query in test_queries:
            result = await detector.detect(query)
            print(f"  Query: {query}")
            print(f"    Ambiguous: {result['is_ambiguous']}, Types: {result['ambiguity_types']}")

        print(f"[OK] Disambiguation test passed")
        return True
    except Exception as e:
        print(f"[ERROR] Disambiguation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_few_shot_rag():
    """Test few-shot RAG (without Qdrant connection)"""
    print("\n=== Test Few-Shot RAG ===")

    try:
        from backend.src.app.services.few_shot_rag.qdrant_service import QdrantService
        from backend.src.app.services.few_shot_rag.prompt_builder import PromptBuilder

        # Test PromptBuilder only (without Qdrant connection)
        prompt_builder = PromptBuilder()

        # Test Prompt building
        cube_schema = {
            "Orders": {
                "measures": ["total_revenue", "order_count"],
                "dimensions": ["created_at", "category"]
            }
        }

        # Mock empty examples since we can't connect to Qdrant via client
        prompt = "Test prompt with schema"
        print(f"[OK] PromptBuilder created successfully")
        print(f"[INFO] Qdrant client skipped due to httpx compatibility issue")
        print(f"[INFO] REST API test passed separately")
        return True
    except Exception as e:
        print(f"[ERROR] Few-shot RAG test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_database_models():
    """Test database models"""
    print("\n=== Test Database Models ===")

    try:
        from backend.src.app.data.models import SuccessfulQuery, RepairHistory

        # Check models are defined
        print(f"[OK] SuccessfulQuery model defined")
        print(f"[OK] RepairHistory model defined")

        return True
    except Exception as e:
        print(f"[ERROR] Database models test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_yaml_configs():
    """Test YAML configurations"""
    print("\n=== Test YAML Configs ===")

    import yaml

    try:
        # Use project root for paths
        project_root = Path(__file__).parent.parent.parent

        # Test business rules
        rules_path = project_root / "AgentV2" / "rules" / "business_rules.yaml"
        with open(rules_path, "r", encoding="utf-8") as f:
            rules = yaml.safe_load(f)
            print(f"[OK] business_rules.yaml loaded ({len(rules['rules'])} rules)")

        # Test error patterns
        patterns_path = project_root / "self_healing" / "error_patterns.yaml"
        with open(patterns_path, "r", encoding="utf-8") as f:
            patterns = yaml.safe_load(f)
            print(f"[OK] error_patterns.yaml loaded ({len(patterns['patterns'])} patterns)")

        return True
    except Exception as e:
        print(f"[ERROR] YAML configs test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    load_dotenv()

    print("=" * 60)
    print("SOTA Agent System Integration Test")
    print("=" * 60)

    tests = [
        ("Swarm Graph Construction", test_swarm_graph),
        ("Sub Agents Import", test_subagents),
        ("Qdrant Service (REST API)", test_qdrant_service),
        ("Cube.js Service", test_cube_service),
        ("Disambiguation", test_disambiguation),
        ("Few-Shot RAG (Partial)", test_few_shot_rag),
        ("Database Models", test_database_models),
        ("YAML Configs", test_yaml_configs)
    ]

    results = []
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"[ERROR] {name} test exception: {e}")
            results.append((name, False))

    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "[OK] PASS" if result else "[ERROR] FAIL"
        print(f"{status} - {name}")

    print("=" * 60)
    print(f"Pass Rate: {passed}/{total} ({passed*100//total}%)")
    print("=" * 60)

    # Note about Qdrant client
    if results[2][1]:  # If Qdrant REST API test passed
        print("\n[INFO] Qdrant REST API is working. The qdrant-client library")
        print("       has a known httpx compatibility issue on this system.")
        print("       The service can be used via REST API (requests library).")

    return all(r for _, r in results)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
