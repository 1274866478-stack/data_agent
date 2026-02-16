# -*- coding: utf-8 -*-
"""
Excel 到 SQLite 转换服务
========================================

在数据源创建时自动将 Excel 文件转换为 SQLite 数据库，
支持完整的 SQL 语法（JOIN, GROUP BY, 聚合函数等）。

作者: BMad Master
版本: 1.0.0
"""

import hashlib
import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)


class ExcelToSQLiteService:
    """
    Excel 到 SQLite 转换服务

    功能:
    - 读取 Excel 文件的所有工作表
    - 转换为 SQLite 数据库
    - 自动推断列类型
    - 创建索引优化查询性能
    """

    # SQLite 数据库存储目录（相对于 backend 目录）
    SQLITE_STORAGE_PATH = Path(__file__).parent.parent.parent / "data" / "sqlite_databases"

    def __init__(self):
        """初始化服务，确保存储目录存在"""
        self.SQLITE_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
        logger.info(f"ExcelToSQLiteService initialized, storage path: {self.SQLITE_STORAGE_PATH}")

    def _resolve_excel_path(self, excel_file_path: str) -> Path:
        """
        解析Excel文件路径（支持Windows路径转换）

        Args:
            excel_file_path: Excel文件路径

        Returns:
            解析后的Path对象
        """
        # 检测Windows路径并转换为容器路径
        if len(excel_file_path) > 1 and excel_file_path[1] == ":" and excel_file_path[0].isalpha():
            # Windows路径：C:\data_agent\scripts\...
            path_obj = Path(excel_file_path)
            if not path_obj.exists():
                # 尝试转换为容器路径
                excel_file_path = self._convert_windows_to_container_path(excel_file_path)
                if excel_file_path:
                    return Path(excel_file_path)
            return path_obj

        return Path(excel_file_path)

    def _convert_windows_to_container_path(self, windows_path: str) -> Optional[str]:
        """
        将Windows路径转换为Docker容器路径

        映射规则（基于docker-compose.yml）：
        - C:\\data_agent\\scripts\\ -> /app/data/
        - C:\\data_agent\\data_storage\\ -> /app/uploads/

        Args:
            windows_path: Windows绝对路径

        Returns:
            容器内路径，如果无法转换返回None
        """
        if not windows_path or "\\" not in windows_path:
            return None

        # 规范化路径
        windows_path = str(Path(windows_path))

        # 项目路径映射
        path_mappings = [
            (r"C:\data_agent\scripts", "/app/data"),
            (r"C:\data_agent\data_storage", "/app/uploads"),
        ]

        for windows_prefix, container_prefix in path_mappings:
            if windows_path.lower().startswith(windows_prefix.lower()):
                # 提取相对路径
                relative_path = windows_path[len(windows_prefix):].lstrip("\\/")
                container_path = str(Path(container_prefix) / relative_path)
                logger.info(f"Converted Windows path: {windows_path} -> {container_path}")
                return container_path

        logger.warning(f"No mapping found for Windows path: {windows_path}")
        return None

    def convert_excel_to_sqlite(
        self,
        excel_file_path: str,
        db_name: Optional[str] = None,
        tenant_id: str = "default_tenant"
    ) -> Tuple[str, Dict[str, any]]:
        """
        将 Excel 文件转换为 SQLite 数据库

        Args:
            excel_file_path: Excel 文件路径
            db_name: 自定义数据库名称（可选）
            tenant_id: 租户 ID

        Returns:
            Tuple: (sqlite_db_path, conversion_metadata)
                - sqlite_db_path: SQLite 数据库文件路径
                - conversion_metadata: 转换元数据信息
        """
        start_time = datetime.now()
        # 使用路径解析器（支持Windows路径转换）
        excel_path = self._resolve_excel_path(excel_file_path)

        if not excel_path.exists():
            raise FileNotFoundError(f"Excel file not found: {excel_file_path}")

        # 生成唯一的数据库名称
        if db_name is None:
            db_name = excel_path.stem

        # 计算文件哈希作为唯一标识
        file_hash = self._calculate_file_hash(excel_path)
        unique_db_name = f"{tenant_id}_{db_name}_{file_hash[:8]}"

        # SQLite 数据库文件路径
        sqlite_db_path = self.SQLITE_STORAGE_PATH / f"{unique_db_name}.db"

        # 检查是否已经转换过
        if sqlite_db_path.exists():
            logger.info(f"SQLite database already exists: {sqlite_db_path}")
            return str(sqlite_db_path), {
                "cached": True,
                "original_file": excel_path.name,
                "converted_at": datetime.fromtimestamp(sqlite_db_path.stat().st_mtime).isoformat()
            }

        logger.info(f"Converting Excel to SQLite: {excel_path} -> {sqlite_db_path}")

        try:
            # 读取 Excel 文件
            excel_file = pd.ExcelFile(excel_path, engine='openpyxl')
            sheet_names = excel_file.sheet_names

            logger.info(f"Found {len(sheet_names)} sheets: {sheet_names}")

            # 创建 SQLite 数据库连接
            conn = sqlite3.connect(str(sqlite_db_path))

            # 转换每个工作表
            table_metadata = {}
            total_rows = 0

            for sheet_name in sheet_names:
                logger.info(f"Converting sheet: {sheet_name}")

                # 读取工作表数据
                df = pd.read_excel(excel_file, sheet_name=sheet_name, engine='openpyxl')

                # 清理列名（移除特殊字符，转小写）
                original_columns = df.columns.tolist()
                df.columns = self._sanitize_column_names(df.columns)

                # 处理空值
                df = df.where(pd.notnull(df), None)

                # 推断并转换数据类型
                df = self._optimize_dtypes(df)

                # 写入 SQLite
                table_name = self._sanitize_table_name(sheet_name)
                df.to_sql(table_name, conn, if_exists='replace', index=False)

                # 创建索引
                self._create_indexes(conn, table_name, df)

                sheet_rows = len(df)
                total_rows += sheet_rows

                table_metadata[table_name] = {
                    "original_sheet": sheet_name,
                    "columns": list(df.columns),
                    "row_count": sheet_rows,
                    "column_types": self._get_column_types(df)
                }

                logger.info(f"  - Table '{table_name}': {sheet_rows} rows, {len(df.columns)} columns")

            # 创建元数据表
            self._create_metadata_table(conn, {
                "original_filename": excel_path.name,
                "conversion_date": datetime.now().isoformat(),
                "tenant_id": tenant_id,
                "total_tables": len(sheet_names),
                "total_rows": total_rows,
                "tables": table_metadata
            })

            conn.commit()
            conn.close()

            conversion_time = (datetime.now() - start_time).total_seconds()

            metadata = {
                "cached": False,
                "original_file": excel_path.name,
                "sqlite_db_path": str(sqlite_db_path),
                "conversion_time_seconds": round(conversion_time, 2),
                "tables": table_metadata,
                "total_tables": len(sheet_names),
                "total_rows": total_rows,
                "converted_at": datetime.now().isoformat()
            }

            logger.info(f"Conversion completed successfully in {conversion_time:.2f}s")

            return str(sqlite_db_path), metadata

        except Exception as e:
            # 清理部分转换的文件
            if sqlite_db_path.exists():
                sqlite_db_path.unlink()

            logger.error(f"Failed to convert Excel to SQLite: {e}")
            raise

    def _calculate_file_hash(self, file_path: Path) -> str:
        """计算文件的 SHA256 哈希值"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _sanitize_column_names(self, columns) -> List[str]:
        """清理列名（移除特殊字符，转小写，添加下划线）"""
        sanitized = []
        for col in columns:
            # 转换为字符串
            col_str = str(col).strip()
            # 移除特殊字符，只保留字母、数字、下划线
            col_str = ''.join(c if c.isalnum() or c in ('_', '-') else '_' for c in col_str)
            # 转小写
            col_str = col_str.lower()
            # 移除连续的下划线
            col_str = '_'.join(filter(None, col_str.split('_')))
            # 确保不以数字开头
            if col_str and col_str[0].isdigit():
                col_str = f'col_{col_str}'
            # 确保不为空
            if not col_str:
                col_str = 'unnamed_column'
            sanitized.append(col_str)
        return sanitized

    def _sanitize_table_name(self, sheet_name: str) -> str:
        """清理表名"""
        # 转小写
        table_name = sheet_name.lower().strip()
        # 移除特殊字符
        table_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in table_name)
        # 移除连续下划线
        table_name = '_'.join(filter(None, table_name.split('_')))
        # 确保不为空
        if not table_name:
            table_name = 'unnamed_table'
        return table_name

    def _optimize_dtypes(self, df: pd.DataFrame) -> pd.DataFrame:
        """优化数据类型以减少存储空间和提高性能"""
        for col in df.columns:
            # 跳过全空列
            if df[col].isna().all():
                continue

            # 尝试转换为数值类型
            try:
                # 检查是否为整数
                if df[col].dtype == 'object':
                    # 尝试转换为整数
                    try:
                        df[col] = pd.to_numeric(df[col], downcast='integer')
                    except ValueError:
                        # 尝试转换为浮点数
                        try:
                            df[col] = pd.to_numeric(df[col], downcast='float')
                        except ValueError:
                            pass
            except Exception:
                pass

            # 尝试转换为日期时间
            try:
                if df[col].dtype == 'object':
                    df[col] = pd.to_datetime(df[col], errors='ignore')
            except Exception:
                pass

        return df

    def _get_column_types(self, df: pd.DataFrame) -> Dict[str, str]:
        """获取每列的数据类型信息"""
        type_mapping = {
            'object': 'TEXT',
            'int64': 'INTEGER',
            'int32': 'INTEGER',
            'int16': 'INTEGER',
            'int8': 'INTEGER',
            'float64': 'REAL',
            'float32': 'REAL',
            'datetime64[ns]': 'DATETIME',
            'bool': 'INTEGER'
        }

        column_types = {}
        for col in df.columns:
            dtype_str = str(df[col].dtype)
            column_types[col] = type_mapping.get(dtype_str, 'TEXT')

        return column_types

    def _create_indexes(self, conn: sqlite3.Connection, table_name: str, df: pd.DataFrame):
        """为表创建索引以提高查询性能"""
        cursor = conn.cursor()

        # 为所有列创建索引（如果列数不太多）
        if len(df.columns) <= 20:
            for col in df.columns:
                try:
                    index_name = f'idx_{table_name}_{col}'
                    cursor.execute(f'CREATE INDEX IF NOT EXISTS {index_name} ON "{table_name}" ("{col}")')
                except Exception as e:
                    logger.warning(f"Failed to create index for {table_name}.{col}: {e}")

        cursor.close()

    def _create_metadata_table(self, conn: sqlite3.Connection, metadata: Dict):
        """创建元数据表存储转换信息"""
        cursor = conn.cursor()

        # 创建元数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS _conversion_metadata (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 插入元数据
        cursor.execute('DELETE FROM _conversion_metadata')
        for key, value in metadata.items():
            if isinstance(value, (dict, list)):
                import json
                value = json.dumps(value, ensure_ascii=False)
            cursor.execute(
                'INSERT INTO _conversion_metadata (key, value) VALUES (?, ?)',
                (key, str(value))
            )

        cursor.close()

    def get_sqlite_connection_string(self, sqlite_db_path: str) -> str:
        """
        获取 SQLite 连接字符串

        Args:
            sqlite_db_path: SQLite 数据库文件路径

        Returns:
            SQLite 连接字符串
        """
        return f"sqlite:///{sqlite_db_path}"

    def delete_sqlite_database(self, sqlite_db_path: str) -> bool:
        """
        删除 SQLite 数据库文件

        Args:
            sqlite_db_path: SQLite 数据库文件路径

        Returns:
            是否删除成功
        """
        try:
            db_path = Path(sqlite_db_path)
            if db_path.exists():
                db_path.unlink()
                logger.info(f"Deleted SQLite database: {sqlite_db_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete SQLite database: {e}")
            return False


# 全局服务实例
_excel_to_sqlite_service: Optional[ExcelToSQLiteService] = None


def get_excel_to_sqlite_service() -> ExcelToSQLiteService:
    """获取 ExcelToSQLiteService 单例实例"""
    global _excel_to_sqlite_service
    if _excel_to_sqlite_service is None:
        _excel_to_sqlite_service = ExcelToSQLiteService()
    return _excel_to_sqlite_service
