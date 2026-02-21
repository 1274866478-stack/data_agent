"""
Database adapter factory and connection manager.

Responsibilities:
- Parse/validate DB connection strings
- Build the proper adapter (PostgreSQL/MySQL/SQLite)
- Enforce read-only SQL safety checks
- Manage named adapter instances in memory
"""

from typing import Dict, Any, Optional, List, Type
from urllib.parse import urlparse
import re
import logging
from dataclasses import dataclass

from .database_interface import (
    DatabaseInterface, DatabaseType, PostgreSQLAdapter,
    MySQLAdapter, SQLiteDatabaseAdapter
)

logger = logging.getLogger(__name__)


@dataclass
class DatabaseCredentials:
    """鏁版嵁搴撹繛鎺ュ嚟鎹?"""
    host: str
    port: int
    database_name: str
    username: str
    password: str
    database_type: DatabaseType
    ssl_mode: Optional[str] = None
    additional_params: Dict[str, Any] = None


class DatabaseConnectionValidator:
    """鏁版嵁搴撹繛鎺ラ獙璇佸櫒"""

    @staticmethod
    def validate_connection_string(connection_string: str) -> bool:
        """
        楠岃瘉鏁版嵁搴撹繛鎺ュ瓧绗︿覆鏍煎紡

        Args:
            connection_string: 鏁版嵁搴撹繛鎺ュ瓧绗︿覆

        Returns:
            bool: 楠岃瘉缁撴灉
        """
        try:
            # 瑙ｆ瀽杩炴帴瀛楃涓?
            parsed = urlparse(connection_string)

            if not parsed.scheme:
                logger.error("Connection string missing scheme")
                return False

            if not parsed.hostname:
                logger.error("杩炴帴瀛楃涓茬己灏戜富鏈哄悕")
                return False

            if not parsed.path or not parsed.path.lstrip('/'):
                logger.error("Connection string missing database name")
                return False

            return True

        except Exception as e:
            logger.error(f"杩炴帴瀛楃涓查獙璇佸け璐? {e}")
            return False

    @staticmethod
    def parse_connection_string(connection_string: str) -> Optional[DatabaseCredentials]:
        """
        瑙ｆ瀽鏁版嵁搴撹繛鎺ュ瓧绗︿覆

        Args:
            connection_string: 鏁版嵁搴撹繛鎺ュ瓧绗︿覆

        Returns:
            DatabaseCredentials: 瑙ｆ瀽鍚庣殑杩炴帴鍑嵁
        """
        try:
            parsed = urlparse(connection_string)

            # 纭畾鏁版嵁搴撶被鍨?
            scheme = parsed.scheme.lower()
            if scheme in ['postgresql', 'postgres']:
                db_type = DatabaseType.POSTGRESQL
                default_port = 5432
            elif scheme == 'mysql':
                db_type = DatabaseType.MYSQL
                default_port = 3306
            elif scheme == 'sqlite':
                db_type = DatabaseType.SQLITE
                default_port = 0
            else:
                logger.error(f"涓嶆敮鎸佺殑鏁版嵁搴撶被鍨? {scheme}")
                return None

            # 瀵逛簬SQLite锛岃矾寰勫氨鏄枃浠惰矾寰?
            if db_type == DatabaseType.SQLITE:
                return DatabaseCredentials(
                    host="",
                    port=0,
                    database_name=parsed.path,
                    username="",
                    password="",
                    database_type=db_type
                )

            # 鎻愬彇杩炴帴鍙傛暟
            port = parsed.port or default_port
            database_name = parsed.path.lstrip('/')

            # 瑙ｆ瀽鏌ヨ鍙傛暟
            query_params = {}
            if parsed.query:
                for param in parsed.query.split('&'):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        query_params[key] = value

            # 鎻愬彇SSL妯″紡
            ssl_mode = query_params.pop('sslmode', None)

            return DatabaseCredentials(
                host=parsed.hostname or "",
                port=port,
                database_name=database_name,
                username=parsed.username or "",
                password=parsed.password or "",
                database_type=db_type,
                ssl_mode=ssl_mode,
                additional_params=query_params
            )

        except Exception as e:
            logger.error(f"瑙ｆ瀽杩炴帴瀛楃涓插け璐? {e}")
            return None

    @staticmethod
    def validate_sql_safety(query: str) -> tuple[bool, Optional[str]]:
        """
        楠岃瘉SQL鏌ヨ瀹夊叏鎬?

        Args:
            query: SQL鏌ヨ璇彞

        Returns:
            tuple: (鏄惁瀹夊叏, 閿欒淇℃伅)
        """
        if not query:
            return False, "鏌ヨ涓嶈兘涓虹┖"

        # 杞崲涓哄ぇ鍐欒繘琛屽叧閿瘝妫€鏌?
        query_upper = query.upper().strip()

        # 妫€鏌ユ槸鍚︿互SELECT寮€澶?
        if not query_upper.startswith('SELECT'):
            return False, "鍙厑璁窼ELECT鏌ヨ"

        # 妫€鏌ュ嵄闄╁叧閿瘝
        dangerous_patterns = [
            r'\bDROP\b',
            r'\bDELETE\b',
            r'\bUPDATE\b',
            r'\bINSERT\b',
            r'\bALTER\b',
            r'\bCREATE\b',
            r'\bTRUNCATE\b',
            r'\bEXEC\b',
            r'\bEXECUTE\b',
            r'\bUNION\b.*\bSELECT\b',  # 绠€鍗曠殑UNION娉ㄥ叆妫€鏌?
            r';\s*(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|TRUNCATE)',  # 澶氳鍙ユ敞鍏?
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, query_upper, re.IGNORECASE):
                return False, f"妫€娴嬪埌涓嶅畨鍏ㄧ殑SQL妯″紡: {pattern}"

        # 妫€鏌ユ煡璇㈠鏉傚害锛堢畝鍗曟鏌ワ級
        if query_upper.count('SELECT') > 5:
            return False, "鏌ヨ杩囦簬澶嶆潅锛屽彲鑳藉寘鍚祵濂楀瓙鏌ヨ"

        if query_upper.count('JOIN') > 10:
            return False, "JOIN鏁伴噺杩囧锛屽彲鑳藉奖鍝嶆€ц兘"

        return True, None


class DatabaseAdapterFactory:
    """鏁版嵁搴撻€傞厤鍣ㄥ伐鍘?"""

    # 娉ㄥ唽鐨勯€傞厤鍣ㄧ被鍨?
    _adapters: Dict[DatabaseType, Type[DatabaseInterface]] = {
        DatabaseType.POSTGRESQL: PostgreSQLAdapter,
        DatabaseType.MYSQL: MySQLAdapter,
        DatabaseType.SQLITE: SQLiteDatabaseAdapter,
    }

    @classmethod
    def register_adapter(cls, db_type: DatabaseType, adapter_class: Type[DatabaseInterface]):
        """
        娉ㄥ唽鏂扮殑鏁版嵁搴撻€傞厤鍣?

        Args:
            db_type: 鏁版嵁搴撶被鍨?
            adapter_class: 閫傞厤鍣ㄧ被
        """
        cls._adapters[db_type] = adapter_class
        logger.info(f"娉ㄥ唽鏁版嵁搴撻€傞厤鍣? {db_type.value} -> {adapter_class.__name__}")

    @classmethod
    def get_supported_types(cls) -> List[DatabaseType]:
        """鑾峰彇鏀寔鐨勬暟鎹簱绫诲瀷鍒楄〃"""
        return list(cls._adapters.keys())

    @classmethod
    def create_adapter(cls, connection_string: str, **kwargs) -> DatabaseInterface:
        """
        鍒涘缓鏁版嵁搴撻€傞厤鍣ㄥ疄渚?

        Args:
            connection_string: 鏁版嵁搴撹繛鎺ュ瓧绗︿覆
            **kwargs: 棰濆鐨勯厤缃弬鏁?

        Returns:
            DatabaseInterface: 鏁版嵁搴撻€傞厤鍣ㄥ疄渚?
        """
        # 楠岃瘉杩炴帴瀛楃涓?
        if not DatabaseConnectionValidator.validate_connection_string(connection_string):
            raise ValueError("Invalid database connection string")

        # 瑙ｆ瀽杩炴帴瀛楃涓?
        credentials = DatabaseConnectionValidator.parse_connection_string(connection_string)
        if not credentials:
            raise ValueError("鏃犳硶瑙ｆ瀽鏁版嵁搴撹繛鎺ュ瓧绗︿覆")

        # 妫€鏌ユ槸鍚︽敮鎸佽鏁版嵁搴撶被鍨?
        if credentials.database_type not in cls._adapters:
            raise ValueError(f"涓嶆敮鎸佺殑鏁版嵁搴撶被鍨? {credentials.database_type.value}")

        # 鑾峰彇閫傞厤鍣ㄧ被
        adapter_class = cls._adapters[credentials.database_type]

        # 鍒涘缓閫傞厤鍣ㄥ疄渚?
        adapter = adapter_class(connection_string, **kwargs)

        logger.info(f"鍒涘缓鏁版嵁搴撻€傞厤鍣? {credentials.database_type.value}")
        return adapter

    @classmethod
    async def create_and_connect(cls, connection_string: str, **kwargs) -> DatabaseInterface:
        """
        鍒涘缓骞惰繛鎺ユ暟鎹簱閫傞厤鍣?

        Args:
            connection_string: 鏁版嵁搴撹繛鎺ュ瓧绗︿覆
            **kwargs: 棰濆鐨勯厤缃弬鏁?

        Returns:
            DatabaseInterface: 宸茶繛鎺ョ殑鏁版嵁搴撻€傞厤鍣ㄥ疄渚?
        """
        adapter = cls.create_adapter(connection_string, **kwargs)

        if not await adapter.connect():
            raise ConnectionError(f"鏃犳硶杩炴帴鍒版暟鎹簱: {connection_string}")

        return adapter

    @classmethod
    async def test_connection(cls, connection_string: str, **kwargs) -> tuple[bool, Optional[str]]:
        """
        娴嬭瘯鏁版嵁搴撹繛鎺?

        Args:
            connection_string: 鏁版嵁搴撹繛鎺ュ瓧绗︿覆
            **kwargs: 棰濆鐨勯厤缃弬鏁?

        Returns:
            tuple: (杩炴帴鎴愬姛, 閿欒淇℃伅)
        """
        try:
            adapter = cls.create_adapter(connection_string, **kwargs)
            success = await adapter.test_connection()

            if success:
                return True, None
            else:
                return False, "杩炴帴娴嬭瘯澶辫触"

        except Exception as e:
            logger.error(f"鏁版嵁搴撹繛鎺ユ祴璇曞紓甯? {e}")
            return False, str(e)


class DatabaseManager:
    """鏁版嵁搴撶鐞嗗櫒"""

    def __init__(self):
        self._connections: Dict[str, DatabaseInterface] = {}
        self.validator = DatabaseConnectionValidator()

    async def add_connection(self, connection_id: str, connection_string: str,
                           **kwargs) -> bool:
        """
        娣诲姞鏁版嵁搴撹繛鎺?

        Args:
            connection_id: 杩炴帴ID
            connection_string: 杩炴帴瀛楃涓?
            **kwargs: 棰濆閰嶇疆鍙傛暟

        Returns:
            bool: 娣诲姞鎴愬姛
        """
        try:
            adapter = await DatabaseAdapterFactory.create_and_connect(
                connection_string, **kwargs
            )
            self._connections[connection_id] = adapter
            logger.info(f"娣诲姞鏁版嵁搴撹繛鎺? {connection_id}")
            return True

        except Exception as e:
            logger.error(f"娣诲姞鏁版嵁搴撹繛鎺ュけ璐? {e}")
            return False

    async def remove_connection(self, connection_id: str) -> bool:
        """
        绉婚櫎鏁版嵁搴撹繛鎺?

        Args:
            connection_id: 杩炴帴ID

        Returns:
            bool: 绉婚櫎鎴愬姛
        """
        try:
            if connection_id in self._connections:
                adapter = self._connections[connection_id]
                await adapter.disconnect()
                del self._connections[connection_id]
                logger.info(f"绉婚櫎鏁版嵁搴撹繛鎺? {connection_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"绉婚櫎鏁版嵁搴撹繛鎺ュけ璐? {e}")
            return False

    def get_connection(self, connection_id: str) -> Optional[DatabaseInterface]:
        """
        鑾峰彇鏁版嵁搴撹繛鎺?

        Args:
            connection_id: 杩炴帴ID

        Returns:
            DatabaseInterface: 鏁版嵁搴撻€傞厤鍣ㄥ疄渚?
        """
        return self._connections.get(connection_id)

    def list_connections(self) -> List[str]:
        """鍒楀嚭鎵€鏈夎繛鎺D"""
        return list(self._connections.keys())

    async def test_all_connections(self) -> Dict[str, tuple[bool, Optional[str]]]:
        """
        娴嬭瘯鎵€鏈夋暟鎹簱杩炴帴

        Returns:
            Dict: 杩炴帴ID -> (娴嬭瘯缁撴灉, 閿欒淇℃伅)
        """
        results = {}
        for connection_id, adapter in self._connections.items():
            try:
                success = await adapter.test_connection()
                results[connection_id] = (success, None if success else "杩炴帴澶辫触")
            except Exception as e:
                results[connection_id] = (False, str(e))

        return results

    async def cleanup_all(self):
        """娓呯悊鎵€鏈夋暟鎹簱杩炴帴"""
        for connection_id in list(self._connections.keys()):
            await self.remove_connection(connection_id)

    async def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """
        鑾峰彇杩炴帴淇℃伅

        Args:
            connection_id: 杩炴帴ID

        Returns:
            Dict: 杩炴帴淇℃伅
        """
        adapter = self.get_connection(connection_id)
        if not adapter:
            return None

        try:
            schema_info = await adapter.get_schema_info()
            return {
                "connection_id": connection_id,
                "database_type": adapter.get_database_type().value,
                "database_name": schema_info.database_name,
                "table_count": len(schema_info.tables),
                "last_updated": schema_info.last_updated.isoformat() if schema_info.last_updated else None,
                "version": schema_info.version
            }
        except Exception as e:
            logger.error(f"鑾峰彇杩炴帴淇℃伅澶辫触: {e}")
            return {
                "connection_id": connection_id,
                "database_type": adapter.get_database_type().value,
                "error": str(e)
            }


# 鍏ㄥ眬鏁版嵁搴撶鐞嗗櫒瀹炰緥
_db_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """鑾峰彇鍏ㄥ眬鏁版嵁搴撶鐞嗗櫒"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def initialize_database_manager() -> DatabaseManager:
    """鍒濆鍖栧叏灞€鏁版嵁搴撶鐞嗗櫒"""
    global _db_manager
    _db_manager = DatabaseManager()
    logger.info("鏁版嵁搴撶鐞嗗櫒鍒濆鍖栧畬鎴?")
    return _db_manager
