# 流式输出失效Bug修复计划

## 问题描述

前端收不到任何流式数据。后端流式端点返回空响应。

## 根本原因

`backend/src/app/api/v2/endpoints/query_stream_v2.py` 中存在**嵌套异步生成器设计缺陷**：

- `send_event` 被定义为 `async def` + `yield`（异步生成器）
- 在外层异步生成器 `event_generator` 中使用 `async for` 迭代它
- 这种嵌套模式导致内部生成器的 `yield` 语句从未执行
- 结果：前端收不到任何流式数据

## 修复方案

### 修改文件

`backend/src/app/api/v2/endpoints/query_stream_v2.py`

### 具体修改

将 `send_event` 从异步生成器改为同步生成器，并将所有 `async for` 调用改为普通 `for` 循环。

#### 1. 修改 send_event 函数定义（第248-252行）

**修改前**：
```python
async def send_event(event_type: str, data: Dict[str, Any]):
    """发送 SSE 事件"""
    event_data = json.dumps(data, ensure_ascii=False)
    yield f"event: {event_type}\n"
    yield f"data: {event_data}\n\n"
```

**修改后**：
```python
def send_event(event_type: str, data: Dict[str, Any]):
    """发送 SSE 事件"""
    event_data = json.dumps(data, ensure_ascii=False)
    yield f"event: {event_type}\n"
    yield f"data: {event_data}\n\n"
```

#### 2. 修改所有 send_event 调用点（约60+处）

将所有的：
```python
async for event in send_event(...):
    yield event
```

改为：
```python
for event in send_event(...):
    yield event
```

### 需要修改的位置

根据 grep 结果，以下行需要修改：
- 第272-279行
- 第285-290行
- 第292-293行
- 第299-304行
- 第306-307行
- 第328-340行
- 第346-350行
- 第358-364行
- 第370-376行
- 第383-389行
- 第393-397行
- 第401-410行
- 第422-428行
- 第435-449行
- 第464-474行
- 第484-497行
- 第507-510行
- 第524-527行
- 第538-545行
- 第560-570行
- 第581-588行
- 第598-608行
- 第616-623行
- 第630-637行
- 第653-662行
- 第668-675行
- 第686-694行
- 第703-707行
- 第721-725行

### 修复后代码结构

```python
async def event_generator() -> AsyncGenerator[str, None]:
    """SSE 事件生成器"""

    def send_event(event_type: str, data: Dict[str, Any]):  # 改为同步函数
        """发送 SSE 事件"""
        event_data = json.dumps(data, ensure_ascii=False)
        yield f"event: {event_type}\n"
        yield f"data: {event_data}\n\n"

    try:
        # ... 现有逻辑 ...

        # 所有调用点改为普通 for 循环
        for event in send_event("start", {...}):
            yield event

        # ... 更多代码 ...
```

## 验证步骤

### 1. 后端验证
```bash
# 重启后端服务
docker-compose restart backend

# 查看日志确认无错误
docker-compose logs -f backend
```

### 2. 健康检查
```bash
# 访问健康检查端点
curl http://localhost:8004/api/v2/query/stream/health

# 预期返回：
# {"status":"healthy","version":"2.0.0","streaming":"enabled","protocol":"Server-Sent Events (SSE)"}
```

### 3. 流式端点测试
```bash
# 使用 curl 测试流式端点
curl -N -X POST http://localhost:8004/api/v2/query/stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"query":"test query"}'

# 预期看到 SSE 事件流：
# event: start
# data: {"query":"test query",...}
#
# event: step
# data: {"step":1,"message":"接收查询",...}
#
# ...
```

### 4. 前端验证
1. 打开浏览器开发者工具 → Network 面板
2. 发起查询请求
3. 观察 `/api/v2/query/stream` 请求：
   - Type: `eventsource`
   - Response Headers: `Content-Type: text/event-stream`
   - 应该看到持续的事件流

### 5. 端到端测试
1. 启动完整应用：`docker-compose up`
2. 登录前端应用
3. 发起一个查询
4. 确认：
   - AI 推理步骤实时显示
   - 进度条正常更新
   - 答案内容流式输出（打字机效果）
   - 最终显示完整的分析结果

## 相关文件

- `backend/src/app/api/v2/endpoints/query_stream_v2.py` - 主要修复文件
- `frontend/src/lib/api-client.ts` - 前端流式客户端（无需修改）
- `frontend/src/store/chatStore.ts` - 状态管理（无需修改）
