"""
密钥轮换模块
实现密钥轮换机制和提醒功能
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class KeyType(Enum):
    """密钥类型枚举"""
    MINIO_ACCESS = "minio_access_key"
    MINIO_SECRET = "minio_secret_key"
    ZHIPU_API = "zhipuai_api_key"
    DATABASE_PASSWORD = "database_password"
    OTHER = "other"


@dataclass
class KeyInfo:
    """密钥信息"""
    key_type: KeyType
    service: str
    last_rotation: Optional[datetime] = None
    rotation_interval_days: int = 90
    is_rotated: bool = False
    rotation_notes: str = ""
    created_at: datetime = None
    next_rotation_date: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

        if self.next_rotation_date is None and self.last_rotation:
            self.next_rotation_date = self.last_rotation + timedelta(days=self.rotation_interval_days)


class KeyRotationManager:
    """密钥轮换管理器"""

    def __init__(self, data_file: str = None):
        self.data_file = Path(data_file or "data/key_rotation.json")
        self.keys_info: Dict[str, KeyInfo] = {}
        self._load_keys_info()

    def _load_keys_info(self) -> None:
        """加载密钥信息"""
        try:
            if self.data_file.exists():
                with open(self.data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                for key_id, key_data in data.items():
                    # 转换字符串格式的日期
                    if key_data.get("last_rotation"):
                        key_data["last_rotation"] = datetime.fromisoformat(key_data["last_rotation"])

                    if key_data.get("created_at"):
                        key_data["created_at"] = datetime.fromisoformat(key_data["created_at"])

                    if key_data.get("next_rotation_date"):
                        key_data["next_rotation_date"] = datetime.fromisoformat(key_data["next_rotation_date"])

                    # 转换key_type为枚举
                    if isinstance(key_data.get("key_type"), str):
                        key_data["key_type"] = KeyType(key_data["key_type"])

                    self.keys_info[key_id] = KeyInfo(**key_data)

            logger.info(f"已加载 {len(self.keys_info)} 个密钥记录")

        except Exception as e:
            logger.error(f"加载密钥信息失败: {str(e)}")
            self.keys_info = {}

    def _save_keys_info(self) -> None:
        """保存密钥信息"""
        try:
            # 确保目录存在
            self.data_file.parent.mkdir(parents=True, exist_ok=True)

            # 转换为可序列化的格式
            serializable_data = {}
            for key_id, key_info in self.keys_info.items():
                data = asdict(key_info)
                # 转换日期为字符串
                if data.get("last_rotation"):
                    data["last_rotation"] = data["last_rotation"].isoformat()
                if data.get("created_at"):
                    data["created_at"] = data["created_at"].isoformat()
                if data.get("next_rotation_date"):
                    data["next_rotation_date"] = data["next_rotation_date"].isoformat()
                # 转换枚举为字符串
                data["key_type"] = data["key_type"].value

                serializable_data[key_id] = data

            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(serializable_data, f, indent=2, ensure_ascii=False)

            logger.info("密钥信息已保存")

        except Exception as e:
            logger.error(f"保存密钥信息失败: {str(e)}")

    def register_key(self,
                    key_id: str,
                    key_type: KeyType,
                    service: str,
                    rotation_interval_days: int = 90,
                    initial_notes: str = "") -> None:
        """注册新密钥"""

        if key_id in self.keys_info:
            logger.warning(f"密钥 {key_id} 已存在，将更新信息")
            key_info = self.keys_info[key_id]
            key_info.key_type = key_type
            key_info.service = service
            key_info.rotation_interval_days = rotation_interval_days
            key_info.rotation_notes = initial_notes
        else:
            key_info = KeyInfo(
                key_type=key_type,
                service=service,
                rotation_interval_days=rotation_interval_days,
                rotation_notes=initial_notes
            )
            self.keys_info[key_id] = key_info

        self._save_keys_info()
        logger.info(f"已注册密钥: {key_id} ({service})")

    def record_rotation(self,
                       key_id: str,
                       rotation_notes: str = "",
                       rotated_by: str = None) -> bool:
        """记录密钥轮换"""

        if key_id not in self.keys_info:
            logger.error(f"未找到密钥: {key_id}")
            return False

        key_info = self.keys_info[key_id]
        key_info.last_rotation = datetime.now()
        key_info.next_rotation_date = key_info.last_rotation + timedelta(days=key_info.rotation_interval_days)
        key_info.is_rotated = True
        key_info.rotation_notes = rotation_notes

        self._save_keys_info()

        # 记录轮换事件
        from src.app.core.config_audit import log_config_change
        log_config_change(
            service=key_info.service,
            change_type="key_rotation",
            reason=f"密钥轮换: {key_id}",
            metadata={
                "key_id": key_id,
                "key_type": key_info.key_type.value,
                "rotated_by": rotated_by or os.environ.get("USER", "unknown"),
                "rotation_notes": rotation_notes,
                "next_rotation_date": key_info.next_rotation_date.isoformat()
            }
        )

        logger.info(f"已记录密钥轮换: {key_id}")
        return True

    def get_rotation_status(self, key_id: str = None) -> Dict[str, Any]:
        """获取密钥轮换状态"""

        if key_id:
            if key_id not in self.keys_info:
                return {"error": f"未找到密钥: {key_id}"}

            return self._get_key_status(self.keys_info[key_id], key_id)

        # 返回所有密钥状态
        all_status = {}
        for kid, key_info in self.keys_info.items():
            all_status[kid] = self._get_key_status(key_info, kid)

        return all_status

    def _get_key_status(self, key_info: KeyInfo, key_id: str) -> Dict[str, Any]:
        """获取单个密钥状态"""

        now = datetime.now()
        days_until_rotation = None
        rotation_status = "unknown"

        if key_info.next_rotation_date:
            days_until_rotation = (key_info.next_rotation_date - now).days

            if days_until_rotation < 0:
                rotation_status = "overdue"
            elif days_until_rotation <= 7:
                rotation_status = "urgent"
            elif days_until_rotation <= 30:
                rotation_status = "warning"
            else:
                rotation_status = "normal"

        return {
            "key_id": key_id,
            "key_type": key_info.key_type.value,
            "service": key_info.service,
            "last_rotation": key_info.last_rotation.isoformat() if key_info.last_rotation else None,
            "next_rotation_date": key_info.next_rotation_date.isoformat() if key_info.next_rotation_date else None,
            "rotation_interval_days": key_info.rotation_interval_days,
            "days_until_rotation": days_until_rotation,
            "rotation_status": rotation_status,
            "is_rotated": key_info.is_rotated,
            "rotation_notes": key_info.rotation_notes,
            "created_at": key_info.created_at.isoformat()
        }

    def get_upcoming_rotations(self, days_ahead: int = 30) -> List[Dict[str, Any]]:
        """获取即将需要轮换的密钥"""

        upcoming = []
        now = datetime.now()
        cutoff_date = now + timedelta(days=days_ahead)

        for key_id, key_info in self.keys_info.items():
            if key_info.next_rotation_date and key_info.next_rotation_date <= cutoff_date:
                upcoming.append(self._get_key_status(key_info, key_id))

        # 按轮换日期排序
        upcoming.sort(key=lambda x: x.get("next_rotation_date", ""))

        return upcoming

    def get_overdue_rotations(self) -> List[Dict[str, Any]]:
        """获取已过期需要轮换的密钥"""

        overdue = []
        now = datetime.now()

        for key_id, key_info in self.keys_info.items():
            if key_info.next_rotation_date and key_info.next_rotation_date < now:
                overdue.append(self._get_key_status(key_info, key_id))

        # 按过期时间排序
        overdue.sort(key=lambda x: x.get("next_rotation_date", ""))

        return overdue

    def generate_rotation_report(self) -> Dict[str, Any]:
        """生成密钥轮换报告"""

        now = datetime.now()
        upcoming = self.get_upcoming_rotations(30)
        overdue = self.get_overdue_rotations()

        # 统计信息
        total_keys = len(self.keys_info)
        never_rotated = len([k for k in self.keys_info.values() if not k.is_rotated])

        # 按服务分组统计
        service_stats = {}
        for key_info in self.keys_info.values():
            service = key_info.service
            if service not in service_stats:
                service_stats[service] = {"total": 0, "upcoming": 0, "overdue": 0}
            service_stats[service]["total"] += 1

        for key in upcoming:
            service = key["service"]
            if service in service_stats:
                service_stats[service]["upcoming"] += 1

        for key in overdue:
            service = key["service"]
            if service in service_stats:
                service_stats[service]["overdue"] += 1

        report = {
            "generated_at": now.isoformat(),
            "summary": {
                "total_keys": total_keys,
                "never_rotated": never_rotated,
                "upcoming_30_days": len(upcoming),
                "overdue": len(overdue)
            },
            "upcoming_rotations": upcoming,
            "overdue_rotations": overdue,
            "service_statistics": service_stats,
            "recommendations": self._generate_rotation_recommendations(upcoming, overdue)
        }

        return report

    def _generate_rotation_recommendations(self,
                                         upcoming: List[Dict[str, Any]],
                                         overdue: List[Dict[str, Any]]) -> List[str]:
        """生成轮换建议"""

        recommendations = []

        if overdue:
            recommendations.append(f"发现 {len(overdue)} 个已过期密钥需要立即轮换")

        if len(upcoming) > 5:
            recommendations.append(f"未来30天内有 {len(upcoming)} 个密钥需要轮换，建议提前准备")

        if not upcoming and not overdue:
            recommendations.append("当前密钥状态良好，无需要立即轮换的密钥")

        # 检查从未轮换的密钥
        never_rotated_count = len([k for k in self.keys_info.values() if not k.is_rotated])
        if never_rotated_count > 0:
            recommendations.append(f"有 {never_rotated_count} 个密钥从未轮换，建议建立定期轮换计划")

        return recommendations

    def setup_default_keys(self) -> None:
        """设置默认的密钥配置"""

        default_keys = [
            ("minio_access_key", KeyType.MINIO_ACCESS, "MinIO", 90),
            ("minio_secret_key", KeyType.MINIO_SECRET, "MinIO", 90),
            ("zhipu_api_key", KeyType.ZHIPU_API, "ZhipuAI", 180),  # API密钥轮换间隔更长
            ("database_password", KeyType.DATABASE_PASSWORD, "PostgreSQL", 120)
        ]

        for key_id, key_type, service, interval in default_keys:
            if key_id not in self.keys_info:
                self.register_key(
                    key_id=key_id,
                    key_type=key_type,
                    service=service,
                    rotation_interval_days=interval,
                    initial_notes="系统自动注册的默认密钥"
                )


# 全局密钥轮换管理器实例
key_rotation_manager = KeyRotationManager()


def setup_key_rotation() -> None:
    """设置密钥轮换的便捷函数"""
    key_rotation_manager.setup_default_keys()


def get_rotation_status(key_id: str = None) -> Dict[str, Any]:
    """获取轮换状态的便捷函数"""
    return key_rotation_manager.get_rotation_status(key_id)


def record_key_rotation(key_id: str, notes: str = "") -> bool:
    """记录密钥轮换的便捷函数"""
    return key_rotation_manager.record_rotation(key_id, notes)