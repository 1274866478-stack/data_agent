"""
配置审计模块
记录和追踪配置变更历史
"""

import json
import os
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ConfigAuditLogger:
    """配置审计日志记录器"""

    def __init__(self, log_dir: str = None):
        self.log_dir = Path(log_dir or "logs/audit")
        self.log_file = self.log_dir / "config_audit.jsonl"
        self._lock = threading.Lock()

        # 确保日志目录存在
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log_change(self,
                  service: str,
                  change_type: str,
                  old_value: Any = None,
                  new_value: Any = None,
                  user: str = None,
                  reason: str = None,
                  metadata: Dict[str, Any] = None) -> None:
        """记录配置变更"""

        with self._lock:
            try:
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "service": service,
                    "change_type": change_type,
                    "user": user or os.environ.get("USER", "unknown"),
                    "process_id": os.getpid(),
                    "hostname": os.environ.get("HOSTNAME", "unknown"),
                    "old_value": self._sanitize_value(old_value),
                    "new_value": self._sanitize_value(new_value),
                    "reason": reason,
                    "metadata": metadata or {}
                }

                # 写入日志文件
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

                logger.info(f"配置变更已记录: {service} - {change_type}")

            except Exception as e:
                logger.error(f"记录配置变更失败: {str(e)}")

    def _sanitize_value(self, value: Any) -> Any:
        """清理敏感信息 - 完全隐藏敏感数据"""
        if value is None:
            return None

        # 将值转换为字符串进行清理
        value_str = str(value)

        # 敏感关键词列表
        sensitive_keywords = [
            "password", "secret", "key", "token", "auth",
            "api_key", "access_key", "private", "credential",
            "jwt", "bearer", "session"
        ]

        # 检查是否包含敏感信息
        value_lower = value_str.lower()
        for keyword in sensitive_keywords:
            if keyword in value_lower:
                # 完全隐藏敏感信息，只显示长度
                return f"***REDACTED*** (length: {len(value_str)})"

        return value

    def get_audit_history(self,
                         service: str = None,
                         change_type: str = None,
                         user: str = None,
                         start_time: datetime = None,
                         end_time: datetime = None,
                         limit: int = 100) -> List[Dict[str, Any]]:
        """获取审计历史"""

        try:
            if not self.log_file.exists():
                return []

            history = []

            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue

                    try:
                        entry = json.loads(line)

                        # 应用过滤条件
                        if service and entry.get("service") != service:
                            continue

                        if change_type and entry.get("change_type") != change_type:
                            continue

                        if user and entry.get("user") != user:
                            continue

                        # 时间范围过滤
                        entry_time = datetime.fromisoformat(entry.get("timestamp"))
                        if start_time and entry_time < start_time:
                            continue

                        if end_time and entry_time > end_time:
                            continue

                        history.append(entry)

                        if len(history) >= limit:
                            break

                    except json.JSONDecodeError:
                        continue

            # 按时间倒序排列
            history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

            return history

        except Exception as e:
            logger.error(f"获取审计历史失败: {str(e)}")
            return []

    def get_security_changes(self, days: int = 30) -> List[Dict[str, Any]]:
        """获取最近的安全相关变更"""

        start_time = datetime.now() - timedelta(days=days)

        security_changes = self.get_audit_history(
            start_time=start_time,
            limit=1000
        )

        # 过滤安全相关的变更
        security_keywords = ["security", "password", "key", "secret", "auth", "minio"]
        filtered_changes = []

        for change in security_changes:
            service = change.get("service", "").lower()
            change_type = change.get("change_type", "").lower()

            if (any(keyword in service for keyword in security_keywords) or
                any(keyword in change_type for keyword in security_keywords)):
                filtered_changes.append(change)

        return filtered_changes

    def get_user_activity(self, user: str, days: int = 30) -> List[Dict[str, Any]]:
        """获取特定用户的活动记录"""

        start_time = datetime.now() - timedelta(days=days)

        return self.get_audit_history(
            user=user,
            start_time=start_time,
            limit=500
        )

    def generate_audit_report(self, days: int = 30) -> Dict[str, Any]:
        """生成审计报告"""

        try:
            start_time = datetime.now() - timedelta(days=days)
            all_changes = self.get_audit_history(start_time=start_time, limit=2000)

            # 统计信息
            total_changes = len(all_changes)
            users = set()
            services = set()
            change_types = {}

            for change in all_changes:
                users.add(change.get("user", "unknown"))
                services.add(change.get("service", "unknown"))

                change_type = change.get("change_type", "unknown")
                change_types[change_type] = change_types.get(change_type, 0) + 1

            # 安全变更
            security_changes = self.get_security_changes(days)

            # 最近的活动
            recent_activity = all_changes[:10]

            report = {
                "generated_at": datetime.now().isoformat(),
                "period_days": days,
                "summary": {
                    "total_changes": total_changes,
                    "unique_users": len(users),
                    "unique_services": len(services),
                    "security_changes": len(security_changes)
                },
                "users": list(users),
                "services": list(services),
                "change_types": change_types,
                "security_changes": security_changes[:20],  # 最近20个安全变更
                "recent_activity": recent_activity,
                "recommendations": self._generate_recommendations(all_changes, security_changes)
            }

            return report

        except Exception as e:
            logger.error(f"生成审计报告失败: {str(e)}")
            return {"error": str(e)}

    def _generate_recommendations(self,
                                all_changes: List[Dict[str, Any]],
                                security_changes: List[Dict[str, Any]]) -> List[str]:
        """基于审计历史生成建议"""

        recommendations = []

        # 检查是否有频繁的密钥变更
        key_changes = [c for c in security_changes if "key" in c.get("service", "").lower()]
        if len(key_changes) > 5:
            recommendations.append("检测到频繁的密钥变更，建议检查是否有异常活动")

        # 检查是否有默认值使用
        default_changes = [c for c in all_changes if "default" in c.get("change_type", "").lower()]
        if default_changes:
            recommendations.append("发现使用默认值的配置，建议修改为安全的自定义值")

        # 检查是否有配置回滚
        rollback_changes = [c for c in all_changes if "rollback" in c.get("change_type", "").lower()]
        if rollback_changes:
            recommendations.append("检测到配置回滚操作，建议确认回滚原因")

        if not recommendations:
            recommendations.append("配置管理活动正常，未发现明显问题")

        return recommendations

    def cleanup_old_logs(self, days_to_keep: int = 90) -> None:
        """清理旧的审计日志"""

        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)

            if not self.log_file.exists():
                return

            # 创建临时文件
            temp_file = self.log_file.with_suffix(".tmp")

            kept_count = 0
            removed_count = 0

            with open(self.log_file, "r", encoding="utf-8") as infile, \
                 open(temp_file, "w", encoding="utf-8") as outfile:

                for line in infile:
                    if not line.strip():
                        continue

                    try:
                        entry = json.loads(line)
                        entry_time = datetime.fromisoformat(entry.get("timestamp"))

                        if entry_time >= cutoff_date:
                            outfile.write(line)
                            kept_count += 1
                        else:
                            removed_count += 1

                    except json.JSONDecodeError:
                        continue

            # 替换原文件
            temp_file.replace(self.log_file)

            logger.info(f"审计日志清理完成: 保留 {kept_count} 条，删除 {removed_count} 条")

        except Exception as e:
            logger.error(f"清理审计日志失败: {str(e)}")


# 全局审计日志实例
config_audit_logger = ConfigAuditLogger()


def log_config_change(service: str,
                     change_type: str,
                     old_value: Any = None,
                     new_value: Any = None,
                     user: str = None,
                     reason: str = None,
                     metadata: Dict[str, Any] = None) -> None:
    """记录配置变更的便捷函数"""
    config_audit_logger.log_change(
        service=service,
        change_type=change_type,
        old_value=old_value,
        new_value=new_value,
        user=user,
        reason=reason,
        metadata=metadata
    )


def get_audit_history(limit: int = 100) -> List[Dict[str, Any]]:
    """获取审计历史的便捷函数"""
    return config_audit_logger.get_audit_history(limit=limit)


def generate_audit_report(days: int = 30) -> Dict[str, Any]:
    """生成审计报告的便捷函数"""
    return config_audit_logger.generate_audit_report(days=days)