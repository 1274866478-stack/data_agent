"""
智谱 AI 客户端
GLM API 调用封装
"""

import zhipuai
from zhipuai import ZhipuAI
from typing import Dict, Any, Optional, List, AsyncGenerator
import logging
import json
import time
import asyncio
import hashlib
import secrets
from datetime import datetime
from functools import wraps

from src.app.core.config import settings
from src.app.core.performance_optimizer import performance_monitor, resource_monitor
from src.app.core.security_monitor import security_monitor, SensitiveDataFilter

logger = logging.getLogger(__name__)


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0,
                      circuit_breaker_threshold: int = 5):
    """
    增强重试装饰器，包含熔断机制
    :param max_retries: 最大重试次数
    :param delay: 初始延迟时间(秒)
    :param backoff: 延迟倍数
    :param circuit_breaker_threshold: 熔断器阈值
    """
    def decorator(func):
        # 熔断器状态
        failure_count = 0
        last_failure_time = None
        circuit_open = False
        reset_timeout = 60  # 熔断器重置时间(秒)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            nonlocal failure_count, last_failure_time, circuit_open

            # 检查熔断器状态
            if circuit_open:
                if time.time() - last_failure_time > reset_timeout:
                    circuit_open = False
                    failure_count = 0
                    logger.info(f"熔断器重置: {func.__name__}")
                else:
                    raise Exception(f"熔断器开启: {func.__name__} 服务暂时不可用")

            try:
                # 如果是协程函数，需要 await
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                # 成功时重置失败计数
                if failure_count > 0:
                    failure_count = 0
                    logger.info(f"服务恢复: {func.__name__}")

                return result

            except Exception as e:
                last_exception = e
                failure_count += 1
                last_failure_time = time.time()

                # 记录详细错误日志（不包含敏感信息）
                error_type = type(e).__name__
                error_msg = str(e)

                # 过滤敏感信息
                safe_error_msg = error_msg
                if "api_key" in error_msg.lower():
                    safe_error_msg = "API key error (sensitive information filtered)"
                if any(keyword in error_msg.lower() for keyword in ["token", "secret", "password"]):
                    safe_error_msg = "Authentication error (sensitive information filtered)"

                logger.error(f"函数 {func.__name__} 第 {failure_count} 次失败: {error_type} - {safe_error_msg}")

                # 检查是否触发熔断器
                if failure_count >= circuit_breaker_threshold:
                    circuit_open = True
                    logger.error(f"熔断器开启: {func.__name__} 失败次数达到阈值 {circuit_breaker_threshold}")

                # 如果是最后一次尝试，直接抛出异常
                if failure_count >= max_retries:
                    logger.error(f"函数 {func.__name__} 在 {max_retries} 次重试后仍然失败")
                    raise

                # 计算延迟时间（指数退避 + 随机抖动）
                base_wait = delay * (backoff ** (failure_count - 1))
                jitter = secrets.randbelow(1000) / 1000  # 0-1秒随机抖动
                wait_time = base_wait + jitter

                logger.warning(f"函数 {func.__name__} 将在 {wait_time:.1f}秒后进行第 {failure_count + 1} 次重试")
                await asyncio.sleep(wait_time)

            # 理论上不会执行到这里
            raise last_exception or Exception("Unknown error in retry decorator")

        return wrapper
    return decorator


class ZhipuAIService:
    """
    智谱 AI API 服务类
    增强版本，支持流式处理、思考模式、智能参数调整和性能监控
    """

    def __init__(self):
        self.client = ZhipuAI(api_key=settings.zhipuai_api_key)
        self.default_model = getattr(settings, 'zhipuai_default_model', 'glm-4-flash')
        self.max_tokens = 4000
        self.temperature = 0.7
        self.rate_limit_delay = 0.1  # 速率限制延迟(秒)

        # 性能监控
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        self.total_response_time = 0
        self.last_performance_log = time.time()

        # 简单内存缓存
        self.cache = {}
        self.cache_max_size = 100
        self.cache_ttl = 300  # 5分钟

        # 思考模式指示词
        self.thinking_indicators = [
            "分析", "比较", "评估", "解释", "设计", "规划",
            "为什么", "如何", "原因", "影响", "建议", "步骤",
            "原理", "机制", "策略", "方案", "优缺点", "详细说明"
        ]

    def _get_cache_key(self, model: str, messages: List[Dict[str, str]],
                      max_tokens: int, temperature: float) -> str:
        """生成缓存键"""
        content = json.dumps([model, messages, max_tokens, temperature], sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()

    def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """获取缓存响应"""
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            if time.time() - cached_data['timestamp'] < self.cache_ttl:
                logger.debug(f"缓存命中: {cache_key[:8]}...")
                return cached_data['response']
            else:
                del self.cache[cache_key]  # 过期删除
        return None

    def _cache_response(self, cache_key: str, response: Dict[str, Any]):
        """缓存响应"""
        # LRU淘汰策略
        if len(self.cache) >= self.cache_max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]['timestamp'])
            del self.cache[oldest_key]

        self.cache[cache_key] = {
            'response': response,
            'timestamp': time.time()
        }

    def _log_performance_metrics(self, operation: str, duration: float, success: bool):
        """记录性能指标"""
        self.request_count += 1
        if success:
            self.success_count += 1
        else:
            self.error_count += 1

        self.total_response_time += duration

        # 每30秒记录一次性能日志
        if time.time() - self.last_performance_log > 30:
            avg_response_time = self.total_response_time / self.request_count if self.request_count > 0 else 0
            success_rate = self.success_count / self.request_count * 100 if self.request_count > 0 else 0

            logger.info(f"ZhipuAI性能统计 - 总请求: {self.request_count}, "
                       f"成功率: {success_rate:.1f}%, "
                       f"平均响应时间: {avg_response_time:.2f}s, "
                       f"缓存大小: {len(self.cache)}")

            # 重置统计
            self.last_performance_log = time.time()

    async def check_connection(self) -> bool:
        """
        检查智谱AI API连接状态
        """
        try:
            logger.info("正在测试智谱AI API连接...")

            # 发送一个简单的测试请求来验证API连接
            response = await self._call_api_with_retry(
                lambda: self.client.chat.completions.create(
                    model=self.default_model,
                    messages=[
                        {"role": "user", "content": "Hello"}
                    ],
                    max_tokens=5
                )
            )

            if response and hasattr(response, 'choices') and response.choices:
                content = response.choices[0].message.content
                logger.info(f"ZhipuAI API connection: OK - Response: {content[:50]}...")
                return True
            else:
                logger.error("ZhipuAI API connection failed: Invalid response structure")
                return False
        except Exception as e:
            logger.error(f"ZhipuAI API connection failed: {e}")
            return False

    def should_enable_thinking(self, messages: List[Dict[str, str]]) -> bool:
        """
        智能判断是否启用思考模式

        Args:
            messages: 对话消息列表

        Returns:
            bool: 是否建议启用思考模式
        """
        try:
            # 获取用户消息内容
            user_content = ""
            for msg in messages:
                if msg.get("role") == "user":
                    user_content += msg.get("content", "") + " "

            user_content = user_content.strip()
            if not user_content:
                return False

            # 检查思考模式指示词
            content_lower = user_content.lower()
            for indicator in self.thinking_indicators:
                if indicator in content_lower:
                    logger.debug(f"检测到思考模式指示词: {indicator}")
                    return True

            # 检查问题复杂度
            if len(user_content) > 200:  # 较长的问题
                return True
            if "？" in user_content or user_content.count("?") > 1:  # 多个问号
                return True
            if "步骤" in user_content or "详细" in user_content:  # 需要详细回答
                return True

            return False
        except Exception as e:
            logger.warning(f"思考模式判断失败: {e}")
            return False

    @retry_on_failure(max_retries=3, delay=0.5)
    async def stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        enable_thinking: Optional[bool] = None,
        show_thinking: bool = True
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式聊天完成，支持思考模式

        Args:
            messages: 对话消息列表
            model: 模型名称
            max_tokens: 最大tokens
            temperature: 温度参数
            enable_thinking: 是否启用思考模式，None表示自动判断
            show_thinking: 是否显示思考过程

        Yields:
            Dict: 流式响应块
        """
        try:
            model = model or self.default_model
            max_tokens = max_tokens or self.max_tokens
            temperature = temperature if temperature is not None else self.temperature

            # 智能思考模式判断
            if enable_thinking is None:
                enable_thinking = self.should_enable_thinking(messages)
                if enable_thinking:
                    logger.info("智能启用智谱AI思考模式")

            # 构建请求参数
            params = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": True
            }

            # 启用思考模式
            if enable_thinking:
                params["thinking"] = {"type": "enabled"}
                logger.debug(f"智谱AI启用思考模式: {model}")

            logger.info(f"开始智谱AI流式调用: {model}, 思考模式: {enable_thinking}")

            # 发起流式请求
            response = self.client.chat.completions.create(**params)

            thinking_started = False
            content_started = False

            # 处理流式响应
            for chunk in response:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta

                    # 输出思考过程
                    if show_thinking and hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                        if not thinking_started:
                            thinking_started = True
                            logger.debug("智谱AI思考过程开始")

                        yield {
                            'type': 'thinking',
                            'content': delta.reasoning_content,
                            'model': model,
                            'finished': False
                        }

                    # 输出正式回复内容
                    elif hasattr(delta, 'content') and delta.content:
                        if not content_started and thinking_started:
                            content_started = True
                            logger.debug("智谱AI从思考过程切换到正式回复")

                        yield {
                            'type': 'content',
                            'content': delta.content,
                            'model': model,
                            'finished': False
                        }

            # 发送完成信号
            yield {
                'type': 'content',
                'content': "",
                'model': model,
                'finished': True
            }

            logger.info("智谱AI流式调用完成")

        except Exception as e:
            logger.error(f"智谱AI流式调用失败: {e}")
            yield {
                'type': 'error',
                'content': f"智谱AI调用出错: {str(e)}",
                'model': model or self.default_model,
                'finished': True
            }

    async def _call_api_with_retry(self, api_call_func, max_retries: int = 3):
        """
        带重试的API调用
        """
        last_exception = None

        for attempt in range(max_retries):
            try:
                # 添加速率限制延迟
                if attempt > 0:
                    await asyncio.sleep(self.rate_limit_delay * (2 ** attempt))

                result = api_call_func()
                return result

            except Exception as e:
                last_exception = e

                # 如果是最后一次尝试，直接抛出异常
                if attempt == max_retries - 1:
                    logger.error(f"API调用在 {max_retries} 次重试后失败: {e}")
                    raise

                # 记录重试信息
                logger.warning(f"API调用第 {attempt + 1} 次失败: {e}，正在重试...")

        raise last_exception

    @performance_monitor("zhipu_chat_completion")
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
        enable_cache: bool = True,
        skip_security_check: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        调用智谱AI聊天完成API
        增强版本，支持缓存和性能监控

        Args:
            skip_security_check: 跳过安全检查（仅用于内部调用如SQL修复）
        """
        start_time = time.time()
        operation = "chat_completion"

        # 安全检查（内部调用可以跳过）
        if not skip_security_check and not security_monitor.check_request_security(
            {"messages": messages, "model": model, "stream": stream},
            source_ip=getattr(self, '_source_ip', None)
        ):
            logger.warning("安全检查失败，拒绝请求")
            return None

        try:
            model = model or self.default_model
            max_tokens = max_tokens or self.max_tokens
            temperature = temperature if temperature is not None else self.temperature

            # 生成缓存键（仅对非流式请求启用缓存）
            cache_key = None
            if not stream and enable_cache:
                cache_key = self._get_cache_key(model, messages, max_tokens, temperature)
                cached_response = self._get_cached_response(cache_key)
                if cached_response:
                    duration = time.time() - start_time
                    self._log_performance_metrics(operation + "_cache_hit", duration, True)
                    return cached_response

            logger.info(f"调用智谱AI API - Model: {model}, Messages: {len(messages)}, Stream: {stream}, Cache: {enable_cache}")

            response = await self._call_api_with_retry(
                lambda: self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=stream
                )
            )

            if stream:
                duration = time.time() - start_time
                self._log_performance_metrics(operation + "_stream", duration, True)
                return response  # 流式响应
            else:
                # 非流式响应，返回结构化数据
                result = {
                    "content": response.choices[0].message.content or "",
                    "role": response.choices[0].message.role,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    } if response.usage else {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    "model": response.model,
                    "created_at": datetime.fromtimestamp(response.created).isoformat(),
                    "finish_reason": response.choices[0].finish_reason
                }

                # 缓存响应（如果启用且响应不为空）
                if enable_cache and cache_key and result["content"].strip():
                    self._cache_response(cache_key, result)

                duration = time.time() - start_time
                self._log_performance_metrics(operation, duration, True)

                logger.info(f"智谱AI调用成功 - Tokens: {result['usage']['total_tokens']}, 耗时: {duration:.2f}s")
                return result

        except Exception as e:
            duration = time.time() - start_time
            self._log_performance_metrics(operation, duration, False)

            # 过滤敏感信息后的错误日志
            safe_error = str(e)
            if "api_key" in safe_error.lower():
                safe_error = "API authentication error (sensitive information filtered)"

            logger.error(f"Chat completion failed ({duration:.2f}s): {safe_error}")
            return None

    async def embedding(
        self,
        texts: List[str],
        model: str = "embedding-2"
    ) -> Optional[List[List[float]]]:
        """
        生成文本嵌入向量
        """
        try:
            logger.info(f"生成文本嵌入 - 文本数量: {len(texts)}, 模型: {model}")

            response = await self._call_api_with_retry(
                lambda: self.client.embeddings.create(
                    model=model,
                    input=texts
                )
            )

            embeddings = [data.embedding for data in response.data]
            logger.info(f"成功生成 {len(texts)} 个文本的嵌入向量")
            return embeddings
        except Exception as e:
            logger.error(f"嵌入向量生成失败: {e}")
            return None

    async def semantic_search(
        self,
        query: str,
        documents: List[str],
        top_k: int = 5
    ) -> Optional[Dict[str, Any]]:
        """
        语义搜索
        """
        try:
            if not documents:
                return {"query": query, "results": [], "total_documents": 0}

            logger.info(f"语义搜索 - 查询: {query[:50]}..., 文档数: {len(documents)}")

            # 为查询和文档生成嵌入
            all_texts = [query] + documents
            embeddings = await self.embedding(all_texts)

            if not embeddings:
                return None

            query_embedding = embeddings[0]
            doc_embeddings = embeddings[1:]

            # 计算余弦相似度
            try:
                from sklearn.metrics.pairwise import cosine_similarity
                import numpy as np

                similarities = cosine_similarity(
                    [query_embedding],
                    doc_embeddings
                )[0]

                # 获取top_k结果
                top_indices = np.argsort(similarities)[::-1][:top_k]

                results = []
                for idx in top_indices:
                    results.append({
                        "document": documents[idx],
                        "similarity": float(similarities[idx]),
                        "index": int(idx)
                    })

                return {
                    "query": query,
                    "results": results,
                    "total_documents": len(documents)
                }
            except ImportError:
                logger.warning("sklearn 和 numpy 不可用，使用简化的相似度计算")
                # 简化的点积相似度计算
                import math

                results = []
                for i, doc_embedding in enumerate(doc_embeddings):
                    # 计算点积相似度
                    similarity = sum(q * d for q, d in zip(query_embedding, doc_embedding))
                    similarity = similarity / (
                        math.sqrt(sum(q * q for q in query_embedding)) *
                        math.sqrt(sum(d * d for d in doc_embedding))
                    )
                    results.append({
                        "document": documents[i],
                        "similarity": float(similarity),
                        "index": i
                    })

                # 排序并取top_k
                results.sort(key=lambda x: x["similarity"], reverse=True)
                results = results[:top_k]

                return {
                    "query": query,
                    "results": results,
                    "total_documents": len(documents)
                }

        except Exception as e:
            logger.error(f"语义搜索失败: {e}")
            return None

    def analyze_conversation_complexity(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        分析对话复杂度，用于智能参数调整

        Args:
            messages: 对话消息列表

        Returns:
            Dict: 复杂度分析结果
        """
        try:
            total_chars = 0
            user_messages = 0
            question_marks = 0
            complex_words = 0

            complexity_words = [
                "分析", "解释", "评估", "比较", "设计", "规划", "策略",
                "为什么", "如何", "原因", "影响", "步骤", "原理",
                "机制", "方案", "优缺点", "详细说明"
            ]

            for msg in messages:
                if msg.get("role") == "user":
                    user_messages += 1
                    content = msg.get("content", "")

                    total_chars += len(content)
                    question_marks += content.count("?") + content.count("？")

                    content_lower = content.lower()
                    for word in complexity_words:
                        if word in content_lower:
                            complex_words += 1

            # 计算复杂度分数
            complexity_score = (
                min(total_chars / 1000, 1.0) * 0.3 +  # 内容长度
                min(user_messages / 5, 1.0) * 0.2 +     # 消息数量
                min(question_marks / 3, 1.0) * 0.3 +    # 问题数量
                min(complex_words / 5, 1.0) * 0.2       # 复杂词汇
            )

            return {
                "complexity_score": round(complexity_score, 3),
                "total_chars": total_chars,
                "user_messages": user_messages,
                "question_marks": question_marks,
                "complex_words": complex_words,
                "recommend_thinking": complexity_score > 0.4,
                "recommend_temperature": round(0.3 + complexity_score * 0.5, 2),
                "recommend_max_tokens": min(2000 + int(complexity_score * 6000), 8000)
            }
        except Exception as e:
            logger.warning(f"对话复杂度分析失败: {e}")
            return {
                "complexity_score": 0.5,
                "recommend_thinking": False,
                "recommend_temperature": 0.7,
                "recommend_max_tokens": 4000
            }

    async def smart_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        auto_adjust_params: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        智能聊天完成，自动调整参数

        Args:
            messages: 对话消息列表
            model: 模型名称
            auto_adjust_params: 是否自动调整参数

        Returns:
            响应结果
        """
        try:
            # 分析对话复杂度
            complexity_analysis = self.analyze_conversation_complexity(messages)
            logger.info(f"对话复杂度分析: {complexity_analysis}")

            # 自动调整参数
            if auto_adjust_params:
                temperature = complexity_analysis.get("recommend_temperature", self.temperature)
                max_tokens = complexity_analysis.get("recommend_max_tokens", self.max_tokens)
                enable_thinking = complexity_analysis.get("recommend_thinking", False)
            else:
                temperature = self.temperature
                max_tokens = self.max_tokens
                enable_thinking = False

            return await self.chat_completion(
                messages=messages,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                enable_thinking=enable_thinking
            )
        except Exception as e:
            logger.error(f"智能聊天完成失败: {e}")
            return None

    async def text_analysis(
        self,
        text: str,
        analysis_type: str = "summary"
    ) -> Optional[str]:
        """
        文本分析（摘要、关键词提取等）
        """
        try:
            if analysis_type == "summary":
                prompt = f"请为以下文本生成简洁的摘要（不超过200字）：\n\n{text}"
            elif analysis_type == "keywords":
                prompt = f"请从以下文本中提取5-10个关键词，用逗号分隔：\n\n{text}"
            elif analysis_type == "sentiment":
                prompt = f"请分析以下文本的情感倾向（积极/消极/中性），并给出评分（0-100）：\n\n{text}"
            elif analysis_type == "topics":
                prompt = f"请从以下文本中识别主要主题，用列表形式输出：\n\n{text}"
            else:
                prompt = f"请分析以下文本：\n\n{text}"

            messages = [
                {"role": "system", "content": "你是一个专业的文本分析师，请准确、简洁地完成分析任务。"},
                {"role": "user", "content": prompt}
            ]

            response = await self.chat_completion(
                messages=messages,
                max_tokens=500,
                temperature=0.3
            )

            if response:
                return response["content"]
            else:
                return None
        except Exception as e:
            logger.error(f"文本分析失败: {e}")
            return None

    async def validate_api_key(self) -> bool:
        """
        验证API密钥是否有效
        """
        return await self.check_connection()

    async def generate_sql_from_natural_language(
        self,
        query: str,
        schema: str,
        db_type: str = "postgresql"
    ) -> Optional[str]:
        """
        将自然语言查询转换为SQL语句

        Args:
            query: 用户的自然语言查询
            schema: 数据库schema信息
            db_type: 数据库类型 (postgresql, mysql, etc.)

        Returns:
            生成的SQL语句或None
        """
        try:
            logger.info(f"生成SQL查询 - 查询: {query[:100]}..., 数据库类型: {db_type}")

            # 构建SQL生成专用prompt
            system_prompt = f"""你是一个专业的SQL查询生成器。请根据用户的自然语言查询和提供的数据库schema，生成准确的SQL语句。

要求：
1. 只返回SQL语句，不要包含任何解释或说明
2. 使用{db_type}语法
3. 确保生成的SQL安全且高效
4. 只使用SELECT查询，禁止UPDATE、DELETE、DROP等危险操作
5. 处理NULL值和字符串转义
6. 使用适当的LIMIT子句限制结果数量
7. 🔴极值查询必须使用 LIMIT 1：当用户问"最大"、"最小"、"最长"、"最短"、"最高"、"最低"、"第一个"、"最早"、"最晚"等极值问题时，必须用 ORDER BY + LIMIT 1 只返回一条记录
   - 例如："谁工作时间最长"→ `ORDER BY hire_date ASC LIMIT 1`
   - 例如："谁薪资最高"→ `ORDER BY salary DESC LIMIT 1`

数据库Schema:
{schema}"""

            user_prompt = f"""请为以下查询生成SQL语句：
{query}"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            response = await self.chat_completion(
                messages=messages,
                max_tokens=1000,
                temperature=0.1  # 低温度确保准确性
            )

            if response and response.get("content"):
                sql_query = response["content"].strip()

                # 清理可能的markdown格式
                if sql_query.startswith("```sql"):
                    sql_query = sql_query[6:]
                if sql_query.startswith("```"):
                    sql_query = sql_query[3:]
                if sql_query.endswith("```"):
                    sql_query = sql_query[:-3]

                sql_query = sql_query.strip()

                # 基本安全检查
                dangerous_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE"]
                sql_upper = sql_query.upper()

                for keyword in dangerous_keywords:
                    if keyword in sql_upper:
                        logger.warning(f"检测到危险SQL关键词: {keyword}")
                        return None

                logger.info(f"成功生成SQL查询: {sql_query[:100]}...")
                return sql_query
            else:
                logger.error("生成SQL查询失败: 无响应内容")
                return None

        except Exception as e:
            logger.error(f"生成SQL查询失败: {e}")
            return None

    async def explain_query_result(
        self,
        query: str,
        sql: str,
        result_data: Dict[str, Any]
    ) -> Optional[str]:
        """
        解释查询结果，提供自然语言描述

        Args:
            query: 原始自然语言查询
            sql: 执行的SQL语句
            result_data: 查询结果数据

        Returns:
            自然语言解释或None
        """
        try:
            logger.info(f"解释查询结果 - 原查询: {query[:50]}...")

            # 构建结果解释prompt
            system_prompt = """你是一个数据分析师。请根据用户的查询和查询结果，提供清晰、有洞察力的自然语言解释。

要求：
1. 直接回答用户的原始问题
2. 提供关键数据点的解释
3. 如果适用，提供趋势或模式分析
4. 语言简洁明了，避免技术术语
5. 如果结果为空，解释可能的原因"""

            result_summary = {
                "row_count": len(result_data.get("data", [])),
                "columns": result_data.get("columns", []),
                "sample_data": result_data.get("data", [])[:5] if result_data.get("data") else []
            }

            user_prompt = f"""用户查询: {query}
执行的SQL: {sql}
查询结果: {result_summary}

请解释这个查询结果。"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            response = await self.chat_completion(
                messages=messages,
                max_tokens=500,
                temperature=0.3
            )

            if response and response.get("content"):
                explanation = response["content"].strip()
                logger.info(f"成功生成查询解释: {explanation[:100]}...")
                return explanation
            else:
                logger.error("生成查询解释失败: 无响应内容")
                return None

        except Exception as e:
            logger.error(f"生成查询解释失败: {e}")
            return None

    async def get_model_info(self, model: str = None) -> Optional[Dict[str, Any]]:
        """
        获取模型信息
        """
        try:
            model = model or self.default_model

            # 通过简单的调用来测试模型可用性
            test_response = await self.chat_completion(
                messages=[
                    {"role": "user", "content": "测试"}
                ],
                model=model,
                max_tokens=10
            )

            if test_response:
                return {
                    "model": model,
                    "status": "available",
                    "max_tokens": self.max_tokens,
                    "supports_streaming": True,
                    "supports_functions": True  # 假设支持函数调用
                }
            else:
                return {
                    "model": model,
                    "status": "unavailable",
                    "error": "Model test failed"
                }

        except Exception as e:
            logger.error(f"获取模型信息失败: {e}")
            return {
                "model": model or self.default_model,
                "status": "error",
                "error": str(e)
            }


# 全局智谱AI服务实例
zhipu_service = ZhipuAIService()