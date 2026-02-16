"""
# API 端点修复 - Reasoning步骤格式化工具

## [HEADER]
**文件名**: reasoning_fix.py
**职责**: 修复reasoning.py中的语法错误，提供格式化工具函数
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本，修复第287行语法错误

## [INPUT]
- reasoning_step对象: 包含step_number, description, reasoning字段

## [OUTPUT]
- 格式化的SSE数据: str - Server-Sent Events格式的JSON数据

## [LINK]
**上游依赖**:
- [reasoning.py](reasoning.py) - 主推理流程模块

**下游依赖**:
- 无 - 独立工具函数

**调用方**:
- reasoning.py模块 - 推理步骤格式化

## [POS]
**路径**: backend/src/app/api/v1/endpoints/reasoning_fix.py
**模块层级**: Level 3 (API → V1 → Endpoints)
**依赖深度**: 3 层
"""

# 修复第287行的语法错误
import json

def format_reasoning_step(step):
    step_data = {
        'type': 'reasoning_step',
        'step': {
            'step_number': step.step_number,
            'description': step.description,
            'reasoning': step.reasoning
        }
    }
    newline = '\n\n'
    return f'data: {json.dumps(step_data)}{newline}'
