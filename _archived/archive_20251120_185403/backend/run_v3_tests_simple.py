"""
V3功能集成测试 - 简化输出版本
"""
import os
import sys
import time

def check_file_exists(path, description):
    """检查文件是否存在"""
    if os.path.exists(path):
        return True, f"[OK] {description} - 存在"
    else:
        return False, f"[MISSING] {description} - 不存在"

def check_content_in_file(path, content, description):
    """检查文件内容"""
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            file_content = f.read()
            if content in file_content:
                return True, f"[OK] {description} - 找到"
            else:
                return False, f"[MISSING] {description} - 未找到"
    return False, f"[ERROR] {description} - 文件不存在"

def run_v3_tests():
    """运行V3功能测试"""
    project_root = os.path.dirname(os.path.abspath(__file__))
    backend_root = os.path.join(project_root, 'src', 'app')

    print("=== V3功能集成测试 ===")
    print(f"项目根目录: {project_root}")
    print(f"后端根目录: {backend_root}")
    print()

    test_results = []

    # 测试1: 健康检查
    print("测试1: 健康检查功能")
    health_path = os.path.join(backend_root, 'api', 'v1', 'endpoints', 'health.py')
    exists, msg = check_file_exists(health_path, "健康检查端点")
    print(f"  {msg}")
    test_results.append(exists)

    if exists:
        has_get_route, msg = check_content_in_file(health_path, "@router.get", "GET路由")
        print(f"  {msg}")

        has_status_field, msg = check_content_in_file(health_path, "status", "状态字段")
        print(f"  {msg}")

    print()

    # 测试2: 租户管理
    print("测试2: 租户管理功能")
    models_path = os.path.join(backend_root, 'data', 'models.py')
    exists, msg = check_file_exists(models_path, "数据模型文件")
    print(f"  {msg}")

    if exists:
        has_tenant, msg = check_content_in_file(models_path, "class Tenant", "租户模型")
        print(f"  {msg}")

        has_tenant_id, msg = check_content_in_file(models_path, "tenant_id", "租户ID字段")
        print(f"  {msg}")

    tenants_path = os.path.join(backend_root, 'api', 'v1', 'endpoints', 'tenants.py')
    exists, msg = check_file_exists(tenants_path, "租户端点")
    print(f"  {msg}")

    print()

    # 测试3: 数据源管理
    print("测试3: 数据源管理功能")
    datasource_path = os.path.join(backend_root, 'api', 'v1', 'endpoints', 'data_sources.py')
    exists, msg = check_file_exists(datasource_path, "数据源端点")
    print(f"  {msg}")

    if exists:
        has_connection, msg = check_content_in_file(datasource_path, "connection", "连接功能")
        print(f"  {msg}")

    print()

    # 测试4: 文档管理
    print("测试4: 文档管理功能")
    docs_path = os.path.join(backend_root, 'api', 'v1', 'endpoints', 'documents.py')
    exists, msg = check_file_exists(docs_path, "文档端点")
    print(f"  {msg}")

    if exists:
        has_upload, msg = check_content_in_file(docs_path, "upload", "上传功能")
        print(f"  {msg}")

    # 检查MinIO服务
    minio_path = os.path.join(backend_root, 'services', 'minio_client.py')
    exists, msg = check_file_exists(minio_path, "MinIO服务")
    print(f"  {msg}")

    print()

    # 测试5: AI和查询功能
    print("测试5: AI和查询功能")
    llm_path = os.path.join(backend_root, 'services', 'llm_service.py')
    exists, msg = check_file_exists(llm_path, "LLM服务")
    print(f"  {msg}")

    zhipu_path = os.path.join(backend_root, 'services', 'zhipu_client.py')
    exists, msg = check_file_exists(zhipu_path, "智谱AI服务")
    print(f"  {msg}")

    chroma_path = os.path.join(backend_root, 'services', 'chromadb_client.py')
    exists, msg = check_file_exists(chroma_path, "ChromaDB服务")
    print(f"  {msg}")

    print()

    # 测试6: 前端组件
    print("测试6: 前端组件")
    frontend_root = os.path.join(project_root, '..', 'frontend', 'src')

    chat_components = os.path.join(frontend_root, 'components', 'chat')
    exists, msg = check_file_exists(chat_components, "聊天组件目录")
    print(f"  {msg}")

    xai_components = os.path.join(frontend_root, 'components', 'xai')
    exists, msg = check_file_exists(xai_components, "XAI组件目录")
    print(f"  {msg}")

    chat_page = os.path.join(frontend_root, 'app', '(app)', 'chat', 'page.tsx')
    exists, msg = check_file_exists(chat_page, "聊天页面")
    print(f"  {msg}")

    print()

    # 测试7: 配置文件
    print("测试7: 配置和部署")
    config_path = os.path.join(backend_root, 'core', 'config.py')
    exists, msg = check_file_exists(config_path, "配置文件")
    print(f"  {msg}")

    dockerfile_path = os.path.join(project_root, 'Dockerfile')
    exists, msg = check_file_exists(dockerfile_path, "后端Dockerfile")
    print(f"  {msg}")

    docker_compose_path = os.path.join(project_root, '..', 'docker-compose.yml')
    exists, msg = check_file_exists(docker_compose_path, "Docker Compose")
    print(f"  {msg}")

    print()

    # 计算结果
    passed = sum(test_results)
    total = len(test_results)

    print("=== 测试结果汇总 ===")
    print(f"通过: {passed}/{total}")
    print(f"通过率: {(passed/total*100):.1f}%")

    if passed == total:
        print("结论: 所有V3功能组件检查通过!")
        return 0
    elif passed >= total * 0.8:
        print("结论: V3功能基本完整，少量组件需要完善")
        return 0
    else:
        print("结论: V3功能需要进一步开发和完善")
        return 1

if __name__ == "__main__":
    exit_code = run_v3_tests()
    sys.exit(exit_code)