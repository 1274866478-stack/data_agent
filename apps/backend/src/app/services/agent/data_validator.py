# -*- coding: utf-8 -*-
"""
# [DATA VALIDATOR] 数据验证模块 - SQL与图表数据一致性验证
## [HEADER]
**文件名**: data_validator.py
**职责**: 验证SQL执行结果与图表配置的一致性，防止LLM幻觉导致的数据不匹配
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-27): 初始版本，实现数据一致性验证和智能字段映射

## [INPUT]
- executed_sql: str - 执行的SQL语句
- query_results: List[Dict[str, Any]] - SQL查询结果
- llm_config: Dict[str, Any] - LLM生成的图表配置（可能包含幻觉字段）
## [OUTPUT]
- ValidationResult: 包含验证结果、字段映射和建议的配置
- FieldMapping: 智能推断的X/Y轴字段映射

## [LINK]
**上游依赖**:
- [models.py](models.py) - ChartType和ChartConfig定义
**下游依赖**:
- [agent_service.py](agent_service.py) - 使用验证结果构建响应
- [data_transformer.py](data_transformer.py) - 使用字段映射转换数据

## [POS]
**路径**: backend/src/app/services/agent/data_validator.py
**模块层级**: Level 3 (Services - Agent Data Validator)
**依赖深度**: 2层
"""
import re
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from pydantic import BaseModel

class ColumnType(str, Enum):
    """列数据类型枚举"""
    TIME = "time"           # 时间/日期类型
    CATEGORY = "category"   # 分类/字符串类型
    NUMERIC = "numeric"     # 数值类型
    UNKNOWN = "unknown"     # 未知类型

class ValidationResult(BaseModel):
    """验证结果"""
    is_valid: bool = False
    error_message: Optional[str] = None
    actual_columns: List[str] = []
    llm_fields: List[str] = []
    hallucinated_fields: List[str] = []  # LLM编造但实际不存在的字段

class FieldMapping(BaseModel):
    """字段映射结果"""
    x_field: Optional[str] = None
    y_field: Optional[str] = None
    x_type: ColumnType = ColumnType.UNKNOWN
    y_type: ColumnType = ColumnType.UNKNOWN
    confidence: float = 0.0  # 0-1, 映射置信度
    reasoning: str = ""

class ChartRecommendation(BaseModel):
    """图表推荐结果"""
    chart_type: str = "table"
    x_field: Optional[str] = None
    y_field: Optional[str] = None
    title: str = "查询结果"
    reasoning: str = ""

class ChartFieldValidation(BaseModel):
    """图表字段一致性验证（对外用实际查询和SQL SELECT）"""
    is_valid: bool = False
    required_fields: List[str] = []
    select_fields: List[str] = []
    data_fields: List[str] = []
    missing_in_select: List[str] = []
    missing_in_data: List[str] = []
    message: Optional[str] = None

class DataConsistencyValidator:
    """数据一致性验证引擎"""
