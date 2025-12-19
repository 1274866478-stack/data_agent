# AI查询处理流程详解

## 概述

本文档详细说明AI助手如何一步一步处理用户查询"列出所有用户的名称"，并生成包含推理过程、数据源引用和可视化图表的完整回答。

## 完整处理流程

### 第一步：接收用户查询

**位置**：`backend/src/app/api/v1/endpoints/query.py`

用户在前端输入查询："列出所有用户的名称"

```466:474:backend/src/app/api/v1/endpoints/query.py
@router.post("/query", response_model=None)
async def create_query(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
    tenant=Depends(get_current_tenant_from_request),
    user_info: Dict[str, Any] = Depends(get_current_user_info_from_request),
    db: Session = Depends(get_db),
    query_service: QueryService = Depends(get_query_service)
):
```

系统创建查询ID，记录开始时间，并提取用户和租户信息。

### 第二步：数据源识别与选择

**位置**：`backend/src/app/api/v1/endpoints/query.py`

系统根据用户选择或自动选择数据源：

```499:512:backend/src/app/api/v1/endpoints/query.py
        # 选择数据源：优先用户指定，否则自动取第一个活跃数据源；后续仅使用这一条
        data_source_id = request.connection_id
        selected_source = None
        
        # 🔍 诊断：记录所有活跃数据源信息
        all_active_sources = await data_source_service.get_data_sources(
            tenant_id=tenant.id,
            db=db,
            active_only=True
        )
        logger.info(f"🔍 [数据源诊断] 租户 {tenant.id} 共有 {len(all_active_sources)} 个活跃数据源:")
        for idx, ds in enumerate(all_active_sources):
            logger.info(f"  [{idx+1}] ID: {ds.id}, 名称: {ds.name}, 类型: {ds.db_type}, 状态: {ds.status}")
```

假设选择的数据源是 `ecommerce_test_data.xlsx`（类型：xlsx）。

### 第三步：问题增强（根据数据源类型）

**位置**：`backend/src/app/api/v1/endpoints/query.py`

系统检测到数据源是Excel文件，会增强问题提示，明确告诉AI必须使用文件工具：

```582:595:backend/src/app/api/v1/endpoints/query.py
                # 🔧 关键修复：根据数据源类型修改问题，明确告诉AI助手数据源类型
                enhanced_question = request.query
                if selected_source.db_type in ["xlsx", "xls", "csv"]:
                    # 文件数据源：明确告诉AI这是文件，必须使用文件工具
                    enhanced_question = f"""【重要提示：当前数据源是{selected_source.db_type.upper()}文件，不是SQL数据库】
                    
你必须：
1. 使用 `inspect_file` 工具查看文件结构和工作表名称（对于Excel文件）
2. 使用 `analyze_dataframe` 或 `python_interpreter` 工具执行Pandas查询
3. **严禁使用SQL工具（query, list_tables, get_schema）**

用户问题：{request.query}"""
                    logger.info(f"🔧 [数据源类型修复] 检测到文件数据源（{selected_source.db_type}），已增强问题提示")
                    print(f"🔧 [数据源类型修复] 检测到文件数据源（{selected_source.db_type}），已增强问题提示")
                    print(f"🔧 [增强后的问题] {enhanced_question[:200]}...")
```

增强后的问题会明确指示AI：
- 这是Excel文件，不是SQL数据库
- 必须使用 `inspect_file` 查看文件结构
- 必须使用 `analyze_dataframe` 执行Pandas查询
- 严禁使用SQL工具

### 第四步：Agent初始化与执行

**位置**：`backend/src/app/services/agent/agent_service.py`

系统调用Agent处理查询：

```694:724:backend/src/app/services/agent/agent_service.py
async def run_agent(
    question: str,
    database_url: str,
    thread_id: str = "default",
    enable_echarts: bool = False,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Run the SQL agent with a user question.

    Args:
        question: User's natural language question
        database_url: PostgreSQL connection string
        thread_id: Session/conversation ID for memory
        enable_echarts: Enable chart generation
        verbose: Enable detailed logging

    Returns:
        Response dictionary with:
        - answer: AI's text response
        - sql: Executed SQL query (if any)
        - data: Query results (if any)
        - success: Whether execution succeeded
        - error: Error message (if failed)
    """
    try:
        # Build or get cached agent
        agent, _ = await build_agent(
            database_url=database_url,
            enable_echarts=enable_echarts,
        )
```

Agent使用LangGraph构建，包含以下组件：
- **LLM**：使用DeepSeek或智谱AI作为语言模型
- **工具节点**：包含文件分析工具（`inspect_file`, `analyze_dataframe`等）
- **系统提示词**：包含详细的指令和规则

### 第五步：系统提示词加载

**位置**：`backend/src/app/services/agent/prompts.py`

Agent加载系统提示词，其中包含关键指令：

```26:142:backend/src/app/services/agent/prompts.py
    prompt = f"""你是一个专业的数据分析助手，支持 SQL 数据库和文件数据源（Excel/CSV），具备数据查询和图表可视化能力。

## 🔴🔴🔴 [CRITICAL INSTRUCTIONS - 最高优先级，违反将导致任务失败] 🔴🔴🔴

**⚠️⚠️⚠️ 以下规则是绝对强制性的，违反将导致任务完全失败：⚠️⚠️⚠️**

### Data Evidence Requirement (数据证据要求)
**Before answering ANY question, you MUST verify that you have received explicit data in the Observation step.**
- 在回答任何问题之前，你必须验证在观察步骤中收到了明确的数据
- 如果没有收到数据，你必须停止并报告错误
- 绝对禁止在没有数据的情况下生成答案

### Anti-Hallucination (反编造规则)
**If the tool returns 'None', 'Error', 'SYSTEM ERROR', empty results, or any error message, you MUST STOP.**
- 如果工具返回 'None'、'Error'、'SYSTEM ERROR'、空结果或任何错误信息，你必须停止
- 绝对禁止编造名称（如 John Doe, 张三, Jane Smith, Bob Johnson 等）
- 绝对禁止编造数字、统计数据或任何数据
- 绝对禁止使用示例数据代替真实数据

### Honest Failure (诚实失败原则)
**It is better to say 'I cannot read the file' or '无法获取数据，请检查数据源连接' than to provide a wrong answer.**
- 说"无法读取文件"或"无法获取数据，请检查数据源连接"比提供错误答案更好
- 诚实告知失败比编造数据更可取
- 用户需要知道真实情况，而不是虚假的答案

### Self-Correction (自我纠正机制)
**Before outputting any data, ask yourself: 'Did I actually read these names/numbers from the tool result?' If not, output an error message instead.**
- 在输出任何数据之前，问自己："我真的从工具结果中读取了这些名称/数字吗？"
- 如果没有，输出错误信息而不是编造数据
- 如果工具返回了 'SYSTEM ERROR' 消息，你必须直接回复："无法获取数据，请检查数据源连接"

### SYSTEM ERROR Handling (系统错误处理)
**If you receive a message starting with 'SYSTEM ERROR:', you MUST immediately stop and reply EXACTLY: "无法获取数据，请检查数据源连接"**
- 如果你收到以 'SYSTEM ERROR:' 开头的消息，你必须立即停止
- 必须准确回复："无法获取数据，请检查数据源连接"
- 绝对禁止尝试解释、修复或生成替代答案

## 🚨 [数据获取与工具使用规则 - 最高优先级]

**⚠️ 违反以下规则将导致任务完全失败，你的回答将被视为无效：**

1. **真实性原则（最高优先级）**：
   - **所有回答必须基于工具 (`Execution Result`) 返回的真实数据**
   - **绝对禁止编造、假设或生成虚假数据**
   - **如果工具返回的数据是中文，回答中必须使用中文数据**
   - **如果工具返回的数据是英文，回答中必须使用英文数据**
   - **严禁在未读取数据的情况下直接生成"准确的答案"**
   - **严禁使用示例数据（如 John Doe, Jane Smith 等）代替真实数据**
   - **如果无法读取数据，必须明确告知用户"无法读取数据"，而不是编造答案**
   - **🚨 如果工具调用失败（返回错误信息），你必须明确告知用户"工具调用失败：[错误信息]"，绝对不要编造数据来替代失败的工具调用结果**
   - **🚨 如果工具返回空数据，你必须明确告知用户"未找到数据"，绝对不要编造数据来填充空结果**

2. **数据源分流**：

   - **当数据源为 SQL 数据库 (Postgres/MySQL)**：

     - 必须优先调用 `list_tables`。

     - 必须使用 `query_database` 执行 SQL。

   - **当数据源为 文件 (Excel/CSV)**：

     - **严禁**使用 SQL 工具。

     - 必须先调用 `inspect_file` (或 `get_column_info`) 查看表头。

     - 必须使用 `analyze_dataframe` (或 `python_interpreter`) 执行 Pandas 查询。

3. **异常处理**：如果无法读取文件，请直接告知用户"无法读取数据"，绝对不要编造数据。
```

系统提示词明确要求：
1. 必须基于真实数据回答，禁止编造
2. 对于Excel文件，必须先调用 `inspect_file` 查看文件结构
3. 必须使用 `analyze_dataframe` 执行Pandas查询
4. 严禁使用SQL工具

### 第六步：工具调用序列

**位置**：`backend/src/app/services/agent/agent_service.py`

Agent按照工作流程执行工具调用：

#### 6.1 调用 `inspect_file` 查看文件结构

Agent首先调用 `inspect_file` 工具查看Excel文件的工作表列表：

```python
# Agent内部执行
tool_call: inspect_file
args: {
    "file_path": "file://data-sources/{tenant_id}/{file_id}.xlsx"
}
```

工具返回：
- 工作表列表：`["users", "orders", "products", ...]`
- 每个工作表的基本信息

#### 6.2 调用 `analyze_dataframe` 读取用户数据

Agent识别到需要查询"users"工作表，调用 `analyze_dataframe` 工具：

**位置**：`backend/src/app/services/agent/tools.py`

```202:326:backend/src/app/services/agent/tools.py
def analyze_dataframe_func(input_data: Dict[str, Any]) -> str:
    """
    使用 Pandas 分析数据文件（Excel/CSV）
    
    支持从 MinIO 下载文件到容器内临时目录，然后使用容器内绝对路径读取
    """
    query = input_data.get("query", "")
    file_path = input_data.get("file_path", "")
    sheet_name = input_data.get("sheet_name", None)
    
    if not query:
        # 🔴 第一道防线：返回特定错误字符串
        return 'SYSTEM ERROR: Tool execution failed or returned no data. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法获取数据，请检查数据源连接"。'
    if not file_path:
        # 🔴 第一道防线：返回特定错误字符串
        return 'SYSTEM ERROR: Tool execution failed or returned no data. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法获取数据，请检查数据源连接"。'
    
    # --- Debug Info ---
    current_dir = os.getcwd()
    logger.info(f"🔍 [Debug] Current Dir: {current_dir}")
    logger.info(f"🔍 [Debug] Input file_path: {file_path}")
    
    # --- 路径修正逻辑 ---
    # 容器内的标准数据目录（挂载了本地 scripts 目录）
    CONTAINER_DATA_DIR = "/app/data"
    
    # 解析文件路径（可能是 MinIO 路径、Windows 路径或容器内路径）
    container_file_path = None
    
    # 检查是否是 MinIO 路径（file://data-sources/...）
    if file_path.startswith("file://"):
        storage_path = file_path[7:]  # 移除 file:// 前缀
        
        # 检查是否是 MinIO 路径（data-sources/...）
        if storage_path.startswith("data-sources/"):
            logger.info(f"🔍 [Debug] 检测到 MinIO 路径，准备下载: {storage_path}")
            
            # 从 MinIO 下载文件
            file_data = minio_service.download_file(
                bucket_name="data-sources",
                object_name=storage_path
            )
            
            if not file_data:
                # 列出当前目录文件，帮助调试
                files_in_dir = os.listdir(current_dir) if os.path.exists(current_dir) else []
                logger.warning(f"⚠️ [第一道防线] 无法从 MinIO 获取文件: {storage_path}. Files in {current_dir}: {files_in_dir}")
                # 🔴 第一道防线：返回特定错误字符串
                return 'SYSTEM ERROR: Tool execution failed or returned no data. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法获取数据，请检查数据源连接"。'
            
            # 保存到容器内临时目录
            temp_dir = os.getenv("TEMP", "/tmp")
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir, exist_ok=True)
            
            # 从路径提取文件名
            filename = os.path.basename(storage_path)
            container_file_path = os.path.join(temp_dir, filename)
            
            # 写入临时文件
            try:
                with open(container_file_path, "wb") as f:
                    f.write(file_data)
                logger.info(f"✅ 文件已下载到容器内路径: {container_file_path}")
            except Exception as e:
                logger.error(f"⚠️ [第一道防线] 写入临时文件失败: {e}", exc_info=True)
                # 🔴 第一道防线：返回特定错误字符串
                return 'SYSTEM ERROR: Tool execution failed or returned no data. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法获取数据，请检查数据源连接"。'
        else:
            # 不是 MinIO 路径，直接使用
            container_file_path = storage_path
    else:
        # 不是 file:// 前缀，可能是 Windows 路径或其他路径
        # 检查是否是 Windows 路径（C:\... 或包含反斜杠）
        if "\\" in file_path or (len(file_path) > 1 and file_path[1] == ":"):
            # Windows 路径，提取文件名并转换为容器内路径
            filename = os.path.basename(file_path)
            container_file_path = os.path.join(CONTAINER_DATA_DIR, filename)
            logger.info(f"🔄 Path Correction: Windows path '{file_path}' -> Container path '{container_file_path}'")
        else:
            # 其他路径，直接使用
            container_file_path = file_path
    
    # 检查文件是否存在
    if not os.path.exists(container_file_path):
        # 尝试在容器数据目录查找
        filename = os.path.basename(container_file_path)
        potential_paths = [
            os.path.join(CONTAINER_DATA_DIR, filename),  # /app/data/filename
            os.path.join(current_dir, filename),  # 当前目录
            container_file_path  # 原始路径
        ]
        
        # 再次列出当前目录和容器数据目录的文件，帮用户找原因
        files_in_current_dir = os.listdir(current_dir) if os.path.exists(current_dir) else []
        files_in_data_dir = os.listdir(CONTAINER_DATA_DIR) if os.path.exists(CONTAINER_DATA_DIR) else []
        logger.warning(f"⚠️ File not found at {container_file_path}")
        logger.warning(f"   Files in {current_dir}: {files_in_current_dir}")
        logger.warning(f"   Files in {CONTAINER_DATA_DIR}: {files_in_data_dir}")
        
        # 尝试所有可能的路径
        for potential_path in potential_paths:
            if os.path.exists(potential_path):
                logger.info(f"✅ Found file at: {potential_path}")
                container_file_path = potential_path
                break
        else:
            # 所有路径都不存在
            logger.warning(f"⚠️ [第一道防线] 文件不存在: {filename}")
            # 🔴 第一道防线：返回特定错误字符串
            return 'SYSTEM ERROR: Tool execution failed or returned no data. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法获取数据，请检查数据源连接"。'
    
    # 读取文件
    try:
        # 根据文件扩展名选择读取方式
        if container_file_path.endswith('.xlsx') or container_file_path.endswith('.xls'):
            # 显式指定 engine='openpyxl' 以确保正确读取
            # 如果指定了工作表名称，使用它；否则读取第一个工作表
            read_params = {"engine": "openpyxl"}
            if sheet_name:
                read_params["sheet_name"] = sheet_name
                logger.info(f"📋 读取Excel工作表: {sheet_name}")
            
            df = pd.read_excel(container_file_path, **read_params)
            logger.info(f"✅ 成功读取 Excel 文件，行数: {len(df)}, 列数: {len(df.columns)}")
```

Agent调用示例：
```python
tool_call: analyze_dataframe
args: {
    "query": "df['user_name'].unique().tolist()",  # 或 "df['user_name'].drop_duplicates().tolist()"
    "file_path": "file://data-sources/{tenant_id}/{file_id}.xlsx",
    "sheet_name": "users"
}
```

工具执行流程：
1. 从MinIO下载文件（如果是MinIO路径）
2. 使用pandas读取Excel文件的"users"工作表
3. 执行Pandas查询：提取 `user_name` 列的唯一值
4. 返回格式化的结果

工具返回结果示例：
```
张三
李四
王五
赵六
钱七
```

### 第七步：LLM生成回答

**位置**：`backend/src/app/services/agent/agent_service.py`

Agent收到工具返回的真实数据后，LLM根据系统提示词生成格式化的回答：

```754:769:backend/src/app/services/agent/agent_service.py
                            if isinstance(msg, AIMessage):
                                print(f"🔥🔥 AIMessage - has content: {bool(msg.content)}, content type: {type(msg.content)}, has tool_calls: {bool(getattr(msg, 'tool_calls', None))}", flush=True)
                                if msg.content:
                                    final_content = msg.content  # 保存最后的AI回复
                                    # 🔥🔥 DEBUG: 打印 LLM 原始输出
                                    print("=" * 80, flush=True)
                                    print("🔥🔥 FINAL LLM OUTPUT (Raw String):", flush=True)
                                    print("=" * 80, flush=True)
                                    print(final_content, flush=True)
                                    print("=" * 80, flush=True)
                                    sys.stdout.flush()
                                    logger.info(f"🔥🔥 FINAL LLM OUTPUT (length: {len(final_content)}): {final_content[:500]}...")
                                elif getattr(msg, 'tool_calls', None):
                                    print(f"🔥🔥 AIMessage has tool_calls but no content. Tool calls: {len(msg.tool_calls)}", flush=True)
                                    sys.stdout.flush()
```

LLM生成的回答包含以下部分（根据系统提示词要求）：

1. **准确的答案 (Accurate Answer)**
   - 基于工具返回的真实数据
   - 列出所有用户名称

2. **引用相关的数据源和文档 (Data Sources)**
   - 数据源：`ecommerce_test_data.xlsx`（工作表名称：`users`）
   - 文档：无

3. **详细的推理过程 (Reasoning)**
   - 说明检查了可用数据源
   - 说明发现了 `users` 工作表
   - 说明提取了 `user_name` 列的唯一值
   - 说明按字母顺序排序（如果需要）

4. **使用Markdown格式化答案 (Markdown Formatting)**
   - 使用Markdown列表格式展示用户名称

5. **可视化 (Visualization)**
   - 虽然问题只是列出名称，但LLM可能会生成一个简单的柱状图配置
   - 使用 `[CHART_START]...{...}[CHART_END]` 格式

### 第八步：图表配置提取

**位置**：`backend/src/app/services/agent/agent_service.py`

系统从LLM回复中提取ECharts JSON配置：

```1025:1060:backend/src/app/services/agent/agent_service.py
        cleaned_content = final_content
        
        if final_content:
            chart_pattern = r'\[CHART_START\]([\s\S]*?)\[CHART_END\]'
            match = re.search(chart_pattern, final_content)
            
            # 🔥🔥 DEBUG: 打印匹配结果
            if match:
                print("=" * 80)
                print("🔥🔥 CHART PATTERN MATCHED!")
                print(f"🔥🔥 Matched JSON string (first 500 chars): {match.group(1)[:500]}")
                print("=" * 80)
                logger.info(f"🔥🔥 CHART PATTERN MATCHED! JSON string length: {len(match.group(1))}")
            else:
                print("=" * 80)
                print("🔥🔥 CHART PATTERN NOT FOUND IN FINAL CONTENT!")
                print("=" * 80)
                logger.warning("🔥🔥 CHART PATTERN NOT FOUND IN FINAL CONTENT!")
            
            if match:
                json_str = match.group(1).strip()
                try:
                    echarts_option_from_text = json.loads(json_str)
                    logger.info("✅ Successfully extracted ECharts JSON configuration from LLM response")
                    
                    # Remove the chart configuration from text content to avoid displaying raw JSON
                    cleaned_content = re.sub(chart_pattern, '', final_content).strip()
                    logger.debug(f"Removed chart configuration from text content. Original length: {len(final_content)}, Cleaned length: {len(cleaned_content)}")
                except json.JSONDecodeError as e:
                    logger.warning(
                        f"⚠️ Failed to parse ECharts JSON configuration from LLM response: {e}. "
                        f"JSON string: {json_str[:200]}..."
                    )
                    # Keep original content if parsing fails
                    cleaned_content = final_content
            else:
                # No chart configuration found, keep original content
                cleaned_content = final_content
```

系统会：
1. 查找 `[CHART_START]...{...}[CHART_END]` 模式
2. 提取其中的JSON配置
3. 从文本内容中移除图表配置（避免显示原始JSON）
4. 将图表配置保存到响应对象中

### 第九步：构建响应对象

**位置**：`backend/src/app/services/agent/agent_service.py`

系统构建 `VisualizationResponse` 对象：

```1301:1326:backend/src/app/services/agent/agent_service.py
        response = VisualizationResponse(
            answer=cleaned_content or "",  # Use cleaned content without JSON configuration
            sql=executed_sql or "",
            data=query_result,
            chart=chart_config,
            echarts_option=echarts_option,
            success=True,
            error=None,
        )

        # Return both dict (backward compatible) and response object
        return {
            "answer": cleaned_content,  # Use cleaned content
            "sql": executed_sql,
            "data": query_results,
            "success": True,
            "error": None,
            "response": response,  # V5.1: structured response
            # 🔴 第三道防线：添加工具调用状态信息供前端使用
            "metadata": {
                "tool_error": tool_error_detected,
                "tool_status": "error" if tool_error_detected else "success",
                "tool_calls": tool_calls_info,
                "reasoning": None  # 可以在这里添加推理过程
            }
        }
```

响应对象包含：
- `answer`：清理后的文本回答（不包含JSON配置）
- `sql`：执行的SQL（对于文件数据源，可能为空）
- `data`：查询结果数据
- `chart`：图表配置对象
- `echarts_option`：ECharts JSON配置
- `success`：是否成功
- `error`：错误信息（如果有）

### 第十步：响应转换与返回

**位置**：`backend/src/app/api/v1/endpoints/query.py`

系统将Agent响应转换为API响应格式并返回给前端：

```634:645:backend/src/app/api/v1/endpoints/query.py
                if agent_response and agent_response.success:
                    # 转换 Agent 响应为 QueryResponseV3 格式
                    processing_time_ms = int((time.time() - start_time) * 1000)
                    response_data = convert_agent_response_to_query_response(
                        agent_response=agent_response,
                        query_id=query_id,
                        tenant_id=tenant.id,
                        original_query=request.query,
                        processing_time_ms=processing_time_ms
                    )
                    agent_success = True
                    return QueryResponseV3(**response_data)
```

## 关键机制说明

### 1. 反编造机制（Anti-Hallucination）

系统通过多层防护确保AI不会编造数据：

1. **系统提示词强制规则**：
   - 必须基于工具返回的真实数据
   - 禁止编造名称、数字或统计数据
   - 如果工具返回错误，必须停止并报告错误

2. **工具层面的检查**：
   - 工具返回空数据时，返回 `SYSTEM ERROR` 消息
   - LLM收到 `SYSTEM ERROR` 时，必须停止并回复错误信息

3. **响应层面的验证**：
   - 检查工具调用是否成功
   - 检查是否有工具错误
   - 在响应元数据中记录工具状态

### 2. 数据源类型识别

系统根据数据源类型自动调整处理流程：

- **SQL数据库**：使用SQL工具（`list_tables`, `get_schema`, `query_database`）
- **文件数据源**：使用文件工具（`inspect_file`, `analyze_dataframe`）

### 3. 路径处理

系统处理多种路径格式：
- MinIO路径：`file://data-sources/{tenant_id}/{file_id}.xlsx`
- Windows路径：`C:\data_agent\scripts\ecommerce_test_data.xlsx`
- 容器内路径：`/app/data/ecommerce_test_data.xlsx`

系统会自动转换路径，确保文件能够正确读取。

### 4. Excel多工作表支持

对于Excel文件，系统支持：
- 读取所有工作表列表
- 指定工作表名称读取特定工作表
- 使用 `sheet_name` 参数指定工作表

## 总结

AI助手处理"列出所有用户名称"查询的完整流程：

1. **接收查询** → 创建查询请求
2. **识别数据源** → 选择Excel文件数据源
3. **增强问题** → 明确告诉AI使用文件工具
4. **初始化Agent** → 加载系统提示词和工具
5. **调用工具** → `inspect_file` → `analyze_dataframe`
6. **读取数据** → 从Excel文件的"users"工作表提取用户名称
7. **生成回答** → 基于真实数据生成格式化的回答
8. **提取图表** → 从回答中提取ECharts配置
9. **构建响应** → 创建结构化响应对象
10. **返回结果** → 将响应返回给前端

整个过程严格遵循"基于真实数据"的原则，通过多层防护机制确保AI不会编造数据。

