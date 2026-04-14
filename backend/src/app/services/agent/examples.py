"""
# Agent Golden Examples - Few-Shot学习示例

## [HEADER]
**文件名**: examples.py
**职责**: 提供Golden Examples帮助LLM理解查询任务，提升Few-Shot学习效果
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本，预留扩展接口

## [INPUT]
- 无直接输入 - 从文件/数据库加载预定义示例

## [OUTPUT]
- 示例字符串: str - 格式化的Golden Examples文本

## [LINK]
**上游依赖**:
- 无 - 未来可从配置文件或数据库加载

**下游依赖**:
- [prompts.py](prompts.py) - 集成到系统提示词

**调用方**:
- System Prompt生成器 - 加载示例并注入提示词

## [POS]
**路径**: backend/src/app/services/agent/examples.py
**模块层级**: Level 3 (Services → Agent → Examples)
**依赖深度**: 2 层
"""


def load_golden_examples() -> str:
    """
    加载黄金示例

    Returns:
        示例字符串，如果为空则返回空字符串
    """
    return """
## 📍 地址/籍贯查询示例

### 示例1：查询用户地址信息
**用户问题**: 张伟是哪里人？
**分析**: 用户询问某人的地址/籍贯信息，需要关联用户表和地址表
**预期SQL**:
```sql
SELECT u.username, a.province, a.city, a.district, a.detail_address
FROM users u
LEFT JOIN addresses a ON u.id = a.user_id
WHERE u.username = '张伟'
ORDER BY a.is_default DESC;
```

### 示例2：查询用户详细地址
**用户问题**: 李明的地址是什么？
**分析**: 用户询问某人的地址，需要关联地址表
**预期SQL**:
```sql
SELECT u.username, a.province, a.city, a.district, a.detail_address
FROM users u
LEFT JOIN addresses a ON u.id = a.user_id
WHERE u.username = '李明'
ORDER BY a.is_default DESC;
```

### 示例3：查询用户来自哪里
**用户问题**: 用户XXX来自哪里？
**分析**: "来自哪里"、"哪里人"都是地址查询的关键词
**预期SQL**:
```sql
SELECT u.username, a.province, a.city, a.district
FROM users u
LEFT JOIN addresses a ON u.id = a.user_id
WHERE u.username = 'XXX';
```

### 示例4：批量查询用户地址
**用户问题**: 各地用户的分布情况如何？
**分析**: 需要按省份/城市统计用户分布
**预期SQL**:
```sql
SELECT a.province, COUNT(DISTINCT u.id) as user_count
FROM users u
LEFT JOIN addresses a ON u.id = a.user_id
GROUP BY a.province
ORDER BY user_count DESC;
```

## 🔑 地址查询关键词识别

当用户问题包含以下关键词时，应该识别为地址/籍贯查询：
- "哪里人"、"哪里来的"、"来自哪里"
- "地址是什么"、"住在哪里"、"居住地"
- "籍贯"、"故乡"、"老家"
- "省份"、"城市"、"地区"

## 📋 地址表关联模式

常见的地址表结构：
```sql
-- users 表（用户表）
users (id, username, email, ...)

-- addresses 表（地址表）
addresses (id, user_id, province, city, district, detail_address, is_default, ...)
```

关联方式：`users.id = addresses.user_id`

查询时使用 LEFT JOIN 以确保即使用户没有地址信息也能返回用户基本信息。
"""

