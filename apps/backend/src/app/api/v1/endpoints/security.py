"""
# [SECURITY] 安全配置和审计API端点

## [HEADER]
**文件名**: security.py
**职责**: 提供安全配置验证、审计报告、密钥轮换状态和推荐
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - 安全端点实现

## [INPUT]
- **GET /security/validate**: 验证安全配置 - 需要认证
- **GET /security/audit**: 生成审计报告 - 参数: days(int)
- **GET /security/audit/history**: 获取审计历史 - 参数: limit(int)
- **GET /security/keys/rotation**: 获取密钥轮换状态 - 需要认证
- **GET /security/keys/report**: 密钥轮换报告 - 需要认证
- **POST /security/keys/record**: 记录密钥轮换 - 需要认证

## [OUTPUT]
- **SecurityConfigResponse**: 安全配置验证结果
- **AuditReportResponse**: 审计报告
- **KeyRotationStatusResponse**: 密钥轮换状态
- **KeyRotationReportResponse**: 密钥轮换报告

## [LINK]
**上游依赖**:
- [../../core/config_validator.py](../../core/config_validator.py)
- [../../core/config_audit.py](../../core/config_audit.py)
- [../../core/key_rotation.py](../../core/key_rotation.py)

**调用方**:
- 安全管理员 - 查看安全状态
- 审计系统 - 生成审计报告
- 密钥管理系统 - 轮换密钥

## [POS]
**路径**: backend/src/app/api/v1/endpoints/security.py
**模块层级**: Level 5
**依赖深度**: 2层
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from src.app.core.config_validator import (
    config_validator,
    validate_security,
    validate_defaults,
    validate_key_strength
)
from src.app.core.config_audit import (
    generate_audit_report,
    get_audit_history
)
from src.app.core.key_rotation import (
    key_rotation_manager,
    get_rotation_status,
    record_key_rotation
)
from src.app.core.auth import get_current_user_with_tenant
from src.app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


# 响应模型
class SecurityValidationResponse(BaseModel):
    service: str
    success: bool
    message: str
    details: Dict[str, Any]
    timestamp: Optional[float] = None


class SecurityConfigResponse(BaseModel):
    overall_status: str
    security_alert: bool
    security_message: str
    total_services: int
    successful: int
    failed: int
    security_issues: int
    results: List[SecurityValidationResponse]
    timestamp: Optional[float] = None


class AuditReportResponse(BaseModel):
    generated_at: str
    period_days: int
    summary: Dict[str, Any]
    users: List[str]
    services: List[str]
    change_types: Dict[str, int]
    security_changes: List[Dict[str, Any]]
    recent_activity: List[Dict[str, Any]]
    recommendations: List[str]


class KeyRotationStatusResponse(BaseModel):
    key_id: str
    key_type: str
    service: str
    last_rotation: Optional[str]
    next_rotation_date: Optional[str]
    rotation_interval_days: int
    days_until_rotation: Optional[int]
    rotation_status: str
    is_rotated: bool
    rotation_notes: str
    created_at: str


class KeyRotationReportResponse(BaseModel):
    generated_at: str
    summary: Dict[str, Any]
    upcoming_rotations: List[KeyRotationStatusResponse]
    overdue_rotations: List[KeyRotationStatusResponse]
    service_statistics: Dict[str, Any]
    recommendations: List[str]


# 安全验证端点
@router.get("/validate", response_model=SecurityConfigResponse)
async def validate_security_configuration(
    current_user: Dict[str, Any] = Depends(get_current_user_with_tenant)
):
    """
    验证安全配置
    """
    try:
        logger.info(f"Security validation requested by user: {current_user.get('sub', 'unknown')}")

        # 执行完整的安全配置验?
        result = await config_validator.validate_all_configs()

        # 转换响应格式
        results = [
            SecurityValidationResponse(**r) for r in result.get("results", [])
        ]

        return SecurityConfigResponse(
            overall_status=result.get("overall_status", "unknown"),
            security_alert=result.get("security_alert", False),
            security_message=result.get("security_message", ""),
            total_services=result.get("total_services", 0),
            successful=result.get("successful", 0),
            failed=result.get("failed", 0),
            security_issues=result.get("security_issues", 0),
            results=results,
            timestamp=result.get("timestamp")
        )

    except Exception as e:
        logger.error(f"Security validation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Security validation failed: {str(e)}")


@router.get("/validate/defaults", response_model=SecurityValidationResponse)
async def validate_secure_defaults(
    current_user: Dict[str, Any] = Depends(get_current_user_with_tenant)
):
    """
    验证安全默认?
    """
    try:
        result = validate_defaults()
        return SecurityValidationResponse(
            service=result.service_name,
            success=result.success,
            message=result.message,
            details=result.details,
            timestamp=result.timestamp
        )
    except Exception as e:
        logger.error(f"Secure defaults validation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.get("/validate/key-strength", response_model=SecurityValidationResponse)
async def validate_security_key_strength(
    current_user: Dict[str, Any] = Depends(get_current_user_with_tenant)
):
    """
    验证密钥强度
    """
    try:
        result = validate_key_strength()
        return SecurityValidationResponse(
            service=result.service_name,
            success=result.success,
            message=result.message,
            details=result.details,
            timestamp=result.timestamp
        )
    except Exception as e:
        logger.error(f"Key strength validation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


# 审计日志端点
@router.get("/audit/report", response_model=AuditReportResponse)
async def get_security_audit_report(
    days: int = Query(default=30, ge=1, le=365, description="报告天数范围"),
    current_user: Dict[str, Any] = Depends(get_current_user_with_tenant)
):
    """
    获取安全审计报告
    """
    try:
        logger.info(f"Audit report requested for {days} days by user: {current_user.get('sub', 'unknown')}")

        report = generate_audit_report(days)
        return AuditReportResponse(**report)

    except Exception as e:
        logger.error(f"Audit report generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Audit report generation failed: {str(e)}")


@router.get("/audit/history")
async def get_security_audit_history(
    service: Optional[str] = Query(default=None, description="服务名称过滤"),
    change_type: Optional[str] = Query(default=None, description="变更类型过滤"),
    limit: int = Query(default=100, ge=1, le=1000, description="返回记录数限制"),
    current_user: Dict[str, Any] = Depends(get_current_user_with_tenant)
):
    """
    获取审计历史记录
    """
    try:
        logger.info(f"Audit history requested by user: {current_user.get('sub', 'unknown')}")

        from src.app.core.config_audit import config_audit_logger
        history = config_audit_logger.get_audit_history(
            service=service,
            change_type=change_type,
            limit=limit
        )

        return {
            "total_records": len(history),
            "filters": {
                "service": service,
                "change_type": change_type,
                "limit": limit
            },
            "records": history
        }

    except Exception as e:
        logger.error(f"Audit history retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Audit history retrieval failed: {str(e)}")


# 密钥轮换端点
@router.get("/key-rotation/status")
async def get_key_rotation_status(
    key_id: Optional[str] = Query(default=None, description="特定密钥ID"),
    current_user: Dict[str, Any] = Depends(get_current_user_with_tenant)
):
    """
    获取密钥轮换状?
    """
    try:
        logger.info(f"Key rotation status requested by user: {current_user.get('sub', 'unknown')}")

        status = get_rotation_status(key_id)

        if key_id and "error" in status:
            raise HTTPException(status_code=404, detail=status["error"])

        return status

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Key rotation status retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Key rotation status retrieval failed: {str(e)}")


@router.get("/key-rotation/report", response_model=KeyRotationReportResponse)
async def get_key_rotation_report(
    current_user: Dict[str, Any] = Depends(get_current_user_with_tenant)
):
    """
    获取密钥轮换报告
    """
    try:
        logger.info(f"Key rotation report requested by user: {current_user.get('sub', 'unknown')}")

        report = key_rotation_manager.generate_rotation_report()

        # 转换响应格式
        upcoming = [KeyRotationStatusResponse(**k) for k in report.get("upcoming_rotations", [])]
        overdue = [KeyRotationStatusResponse(**k) for k in report.get("overdue_rotations", [])]

        return KeyRotationReportResponse(
            generated_at=report.get("generated_at", ""),
            summary=report.get("summary", {}),
            upcoming_rotations=upcoming,
            overdue_rotations=overdue,
            service_statistics=report.get("service_statistics", {}),
            recommendations=report.get("recommendations", [])
        )

    except Exception as e:
        logger.error(f"Key rotation report generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Key rotation report generation failed: {str(e)}")


@router.post("/key-rotation/record")
async def record_key_rotation_event(
    key_id: str,
    notes: str = "",
    current_user: Dict[str, Any] = Depends(get_current_user_with_tenant)
):
    """
    记录密钥轮换事件
    """
    try:
        logger.info(f"Key rotation recording requested by user: {current_user.get('sub', 'unknown')}")

        success = record_key_rotation(
            key_id=key_id,
            notes=notes
        )

        if success:
            return {
                "message": f"Key rotation recorded successfully for {key_id}",
                "key_id": key_id,
                "recorded_by": current_user.get("sub", "unknown"),
                "notes": notes,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail=f"Key not found: {key_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Key rotation recording failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Key rotation recording failed: {str(e)}")


# 综合安全状态端?
@router.get("/dashboard")
async def get_security_dashboard(
    current_user: Dict[str, Any] = Depends(get_current_user_with_tenant)
):
    """
    获取综合安全状态仪表板
    """
    try:
        logger.info(f"Security dashboard requested by user: {current_user.get('sub', 'unknown')}")

        # 获取各种安全状?
        security_validation = await validate_security()
        audit_report = generate_audit_report(7)  # 最?天的审计报告
        rotation_report = key_rotation_manager.generate_rotation_report()

        # 获取即将需要轮换的密钥
        upcoming_rotations = key_rotation_manager.get_upcoming_rotations(30)
        overdue_rotations = key_rotation_manager.get_overdue_rotations()

        # 计算安全评分
        security_score = _calculate_security_score(security_validation, upcoming_rotations, overdue_rotations)

        return {
            "generated_at": datetime.now().isoformat(),
            "security_score": security_score,
            "validation_status": {
                "service": security_validation.service_name,
                "success": security_validation.success,
                "message": security_validation.message,
                "details": security_validation.details
            },
            "audit_summary": {
                "total_changes": audit_report.get("summary", {}).get("total_changes", 0),
                "security_changes": audit_report.get("summary", {}).get("security_changes", 0),
                "unique_users": audit_report.get("summary", {}).get("unique_users", 0)
            },
            "key_rotation_summary": {
                "total_keys": rotation_report.get("summary", {}).get("total_keys", 0),
                "upcoming_30_days": len(upcoming_rotations),
                "overdue": len(overdue_rotations),
                "never_rotated": rotation_report.get("summary", {}).get("never_rotated", 0)
            },
            "alerts": _generate_security_alerts(security_validation, upcoming_rotations, overdue_rotations),
            "recommendations": rotation_report.get("recommendations", [])
        }

    except Exception as e:
        logger.error(f"Security dashboard generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Security dashboard generation failed: {str(e)}")


def _calculate_security_score(security_validation, upcoming_rotations, overdue_rotations) -> Dict[str, Any]:
    """计算安全评分"""

    score = 100
    issues = []

    # 安全验证影响
    if not security_validation.success:
        score -= 30
        issues.append("安全配置验证失败")

    security_details = security_validation.details or {}
    if security_details.get("overall_security_level") == "unsafe":
        score -= 20
        issues.append("检测到安全风险")

    # 密钥轮换影响
    if overdue_rotations:
        score -= len(overdue_rotations) * 10
        issues.append(f"{len(overdue_rotations)} 个密钥已过期")

    if upcoming_rotations:
        score -= len(upcoming_rotations) * 2
        issues.append(f"{len(upcoming_rotations)} 个密钥即将过期")

    # 确保分数不低于0
    score = max(0, score)

    # 确定等级
    if score >= 90:
        grade = "A"
        level = "优秀"
    elif score >= 80:
        grade = "B"
        level = "良好"
    elif score >= 70:
        grade = "C"
        level = "一?
    elif score >= 60:
        grade = "D"
        level = "较差"
    else:
        grade = "F"
        level = "危险"

    return {
        "score": score,
        "grade": grade,
        "level": level,
        "issues": issues
    }


def _generate_security_alerts(security_validation, upcoming_rotations, overdue_rotations) -> List[Dict[str, Any]]:
    """生成安全警报"""

    alerts = []

    # 安全配置警报
    if not security_validation.success:
        alerts.append({
            "type": "error",
            "title": "安全配置验证失败",
            "message": security_validation.message,
            "priority": "high"
        })

    # 过期密钥警报
    if overdue_rotations:
        alerts.append({
            "type": "error",
            "title": "密钥已过?,
            "message": f"发现 {len(overdue_rotations)} 个已过期密钥需要立即轮?,
            "priority": "high"
        })

    # 即将到期密钥警报
    if upcoming_rotations:
        alerts.append({
            "type": "warning",
            "title": "密钥即将到期",
            "message": f"未来30天内?{len(upcoming_rotations)} 个密钥需要轮?,
            "priority": "medium"
        })

    return alerts
