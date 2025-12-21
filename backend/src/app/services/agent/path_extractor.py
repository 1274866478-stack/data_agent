"""
路径提取工具 - 从数据源配置中提取文件路径
支持 connection_config 字段（JSON或字符串）和 connection_string 字段
"""
import json
import logging
import os
import glob
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# 容器内的标准数据目录
CONTAINER_UPLOADS_DIR = "/app/uploads"
CONTAINER_DATA_DIR = "/app/data"


def extract_file_path_from_config(connection_config: Any, connection_string: Optional[str] = None) -> Optional[str]:
    """
    从连接配置中提取文件路径
    
    支持多种格式：
    1. connection_config 是字典/JSON：提取 'path' 或 'uri' 字段
    2. connection_config 是字符串：直接使用
    3. connection_string：作为后备选项
    
    Args:
        connection_config: 连接配置（可能是字典、JSON字符串或普通字符串）
        connection_string: 连接字符串（后备选项）
    
    Returns:
        提取的文件路径，如果提取失败返回None
    """
    try:
        # 优先使用 connection_config
        if connection_config is not None:
            # 如果是字符串，尝试解析为JSON
            if isinstance(connection_config, str):
                # 尝试解析为JSON
                try:
                    config_dict = json.loads(connection_config)
                    if isinstance(config_dict, dict):
                        # 从字典中提取路径
                        path = config_dict.get('path') or config_dict.get('uri') or config_dict.get('file_path')
                        if path:
                            logger.info(f"从connection_config JSON中提取路径: {path}")
                            return path
                except (json.JSONDecodeError, ValueError):
                    # 不是JSON，直接作为路径使用
                    logger.info(f"connection_config是字符串，直接使用: {connection_config}")
                    return connection_config
            
            # 如果是字典
            elif isinstance(connection_config, dict):
                path = connection_config.get('path') or connection_config.get('uri') or connection_config.get('file_path')
                if path:
                    logger.info(f"从connection_config字典中提取路径: {path}")
                    return path
        
        # 如果connection_config没有提供有效路径，使用connection_string作为后备
        if connection_string:
            logger.info(f"使用connection_string作为路径: {connection_string}")
            return connection_string
        
        logger.warning("无法从connection_config或connection_string中提取路径")
        return None
        
    except Exception as e:
        logger.error(f"提取文件路径时出错: {e}", exc_info=True)
        return None


def resolve_file_path_with_fallback(file_path: str) -> Optional[str]:
    """
    解析文件路径并应用本地回退逻辑
    
    支持多种路径格式：
    1. local:///app/uploads/... -> /app/uploads/...
    2. file://data-sources/... -> 尝试从MinIO下载，失败时回退到本地
    3. 容器内绝对路径（如 /app/uploads/...）-> 验证并回退
    4. Windows路径 -> 转换为容器内路径
    
    Args:
        file_path: 原始文件路径
    
    Returns:
        解析后的容器内文件路径，如果解析失败返回None
    """
    if not file_path:
        return None
    
    # 1. 本地存储路径（local:///app/uploads/...）
    if file_path.startswith("local://"):
        container_path = file_path[8:]  # 移除 local:// 前缀
        if os.path.exists(container_path):
            logger.info(f"找到本地存储路径: {container_path}")
            return container_path
        # 尝试回退到 /app/uploads
        fallback = container_path.replace("/app/uploads", "").lstrip("/")
        fallback_path = os.path.join(CONTAINER_UPLOADS_DIR, fallback)
        if os.path.exists(fallback_path):
            logger.info(f"本地回退找到文件: {fallback_path}")
            return fallback_path
    
    # 2. 容器内绝对路径（如 /app/uploads/data-sources/...）
    elif file_path.startswith("/"):
        if os.path.exists(file_path):
            logger.info(f"找到容器内绝对路径: {file_path}")
            return file_path
        # 尝试在 /app/uploads 中查找
        if "data-sources" in file_path or "uploads" in file_path:
            filename = os.path.basename(file_path)
            fallback_path = os.path.join(CONTAINER_UPLOADS_DIR, "data-sources", filename)
            if os.path.exists(fallback_path):
                logger.info(f"本地回退找到文件: {fallback_path}")
                return fallback_path
            # 尝试在 /app/data 中查找
            data_fallback = os.path.join(CONTAINER_DATA_DIR, filename)
            if os.path.exists(data_fallback):
                logger.info(f"数据目录回退找到文件: {data_fallback}")
                return data_fallback
    
    # 3. file:// 路径（可能是MinIO路径或Windows绝对路径）
    elif file_path.startswith("file://"):
        storage_path = file_path[7:]  # 移除 file:// 前缀
        
        # 3.1 Windows绝对路径（如 file://C:\... 或 file:///C:\...）
        if len(storage_path) > 0 and (storage_path[0].isalpha() and len(storage_path) > 1 and storage_path[1] == ":") or \
           (storage_path.startswith("/") and len(storage_path) > 2 and storage_path[1].isalpha() and storage_path[2] == ":"):
            # 移除开头的斜杠（如果有）
            if storage_path.startswith("/"):
                storage_path = storage_path[1:]
            # 直接使用Windows路径
            if os.path.exists(storage_path):
                logger.info(f"找到Windows绝对路径: {storage_path}")
                return storage_path
            logger.warning(f"Windows路径不存在: {storage_path}")
            return None
        
        # 3.2 MinIO路径（file://data-sources/...）- 需要从MinIO下载或本地查找
        elif storage_path.startswith("data-sources/"):
            # 首先尝试从本地文件系统查找
            local_paths = [
                os.path.join(CONTAINER_UPLOADS_DIR, storage_path),  # /app/uploads/data-sources/...
                os.path.join(CONTAINER_DATA_DIR, os.path.basename(storage_path)),  # /app/data/filename
            ]
            for local_path in local_paths:
                if os.path.exists(local_path):
                    logger.info(f"本地回退找到MinIO路径对应的文件: {local_path}")
                    return local_path
            # 如果本地没有找到，返回原始路径（让调用者处理MinIO下载）
            logger.info(f"MinIO路径需要下载: {storage_path}")
            return file_path
        
        # 3.3 其他file://路径，尝试直接使用（可能是相对路径或Unix路径）
        else:
            if os.path.exists(storage_path):
                logger.info(f"找到file://路径对应的文件: {storage_path}")
                return storage_path
            logger.warning(f"无法解析file://路径: {file_path}")
            return None
    
    # 4. Windows路径（包含反斜杠或盘符）
    elif "\\" in file_path or (len(file_path) > 1 and file_path[1] == ":"):
        filename = os.path.basename(file_path)
        container_path = os.path.join(CONTAINER_DATA_DIR, filename)
        logger.info(f"Windows路径转换: {file_path} -> {container_path}")
        if os.path.exists(container_path):
            return container_path
        # 尝试在 /app/uploads 中查找
        uploads_path = os.path.join(CONTAINER_UPLOADS_DIR, filename)
        if os.path.exists(uploads_path):
            return uploads_path
    
    # 5. 相对路径或其他格式
    else:
        # 尝试在标准目录中查找
        potential_paths = [
            os.path.join(CONTAINER_UPLOADS_DIR, file_path),
            os.path.join(CONTAINER_DATA_DIR, file_path),
            os.path.join(CONTAINER_DATA_DIR, os.path.basename(file_path)),
        ]
        for potential_path in potential_paths:
            if os.path.exists(potential_path):
                logger.info(f"找到文件: {potential_path}")
                return potential_path
    
    logger.warning(f"无法解析或找到文件: {file_path}")
    return None


def get_latest_excel_file(base_dir: str = CONTAINER_UPLOADS_DIR) -> str:
    """
    动态查找上传目录中最新的Excel文件
    
    递归搜索指定目录下的所有.xlsx和.xls文件，选择最近修改的文件。
    如果找不到任何文件，抛出FileNotFoundError以防止AI编造数据。
    
    Args:
        base_dir: 搜索的基础目录，默认为 /app/uploads
    
    Returns:
        最新Excel文件的完整路径
    
    Raises:
        FileNotFoundError: 如果找不到任何Excel文件
    """
    # 递归搜索所有Excel文件
    search_pattern = os.path.join(base_dir, "**", "*.xlsx")
    found_files = glob.glob(search_pattern, recursive=True)
    
    # 也搜索.xls文件
    search_pattern_xls = os.path.join(base_dir, "**", "*.xls")
    found_files.extend(glob.glob(search_pattern_xls, recursive=True))
    
    if not found_files:
        error_msg = f"System Error: No Excel files found in {base_dir}. Please confirm upload."
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    
    # 选择最近修改的文件
    latest_file = max(found_files, key=os.path.getmtime)
    logger.info(f"[System Log] Loading actual file: {latest_file}")
    
    return latest_file

