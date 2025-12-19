"""
AI助手编造数据问题诊断测试脚本

使用方法:
    python scripts/test_ai_hallucination.py [test_name]

测试名称:
    - tool_calls: 测试工具调用
    - agent_simple: 测试简单Agent查询
    - data_consistency: 测试数据一致性
    - all: 运行所有测试
"""
import asyncio
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
backend_dir = project_root / "backend"
backend_src = backend_dir / "src"

# 关键：backend使用 from src.app... 导入，所以需要将backend目录添加到路径
# 这样Python可以找到backend/src/app/...作为src.app
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_src))
sys.path.insert(0, str(project_root))

# 设置环境变量，确保可以正确导入
os.environ.setdefault('PYTHONPATH', str(backend_dir))

# 加载环境变量文件（处理编码问题）
env_files = [
    project_root / "backend" / ".env",
    project_root / "Agent" / ".env",
    project_root / ".env"
]

for env_file in env_files:
    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file, encoding='utf-8')
        except Exception:
            # 如果UTF-8失败，尝试其他编码
            try:
                load_dotenv(env_file, encoding='gbk')
            except Exception:
                pass

# 设置输出编码为 UTF-8（Windows兼容）
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 设置日志
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestReporter:
    """测试报告生成器"""
    
    def __init__(self):
        self.results = []
        self.start_time = datetime.now()
    
    def add_result(self, test_name: str, passed: bool, details: Dict[str, Any]):
        """添加测试结果"""
        self.results.append({
            "test_name": test_name,
            "passed": passed,
            "timestamp": datetime.now().isoformat(),
            "details": details
        })
    
    def generate_report(self) -> str:
        """生成测试报告"""
        report = []
        report.append("=" * 80)
        report.append("AI助手编造数据问题诊断测试报告")
        report.append("=" * 80)
        report.append(f"测试开始时间: {self.start_time.isoformat()}")
        report.append(f"测试结束时间: {datetime.now().isoformat()}")
        report.append("")
        
        # 统计
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        failed = total - passed
        
        report.append(f"测试总数: {total}")
        report.append(f"通过: {passed}")
        report.append(f"失败: {failed}")
        report.append("")
        
        # 详细结果
        report.append("-" * 80)
        report.append("详细测试结果")
        report.append("-" * 80)
        
        for result in self.results:
            status = "[PASS]" if result["passed"] else "[FAIL]"
            report.append(f"\n{status} - {result['test_name']}")
            report.append(f"  时间: {result['timestamp']}")
            
            if result["details"]:
                report.append("  详情:")
                for key, value in result["details"].items():
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value, ensure_ascii=False, indent=2)
                    report.append(f"    {key}: {value}")
        
        # 问题总结
        failed_tests = [r for r in self.results if not r["passed"]]
        if failed_tests:
            report.append("")
            report.append("-" * 80)
            report.append("发现的问题")
            report.append("-" * 80)
            for result in failed_tests:
                report.append(f"\n[FAIL] {result['test_name']}")
                if "error" in result["details"]:
                    report.append(f"  错误: {result['details']['error']}")
                if "suggestion" in result["details"]:
                    report.append(f"  建议: {result['details']['suggestion']}")
        
        return "\n".join(report)
    
    def save_report(self, filepath: str):
        """保存测试报告到文件"""
        report = self.generate_report()
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report)
        logger.info(f"测试报告已保存到: {filepath}")


async def test_tool_calls(reporter: TestReporter):
    """测试1: 验证工具调用"""
    logger.info("=" * 80)
    logger.info("测试1: 验证工具调用")
    logger.info("=" * 80)
    
    try:
        # 尝试导入Agent相关模块
        # 注意：backend使用 from src.app... 导入，所以需要将backend/src添加到路径
        try:
            from src.app.services.agent.tools import (
                list_available_tables,
                get_table_schema,
                execute_sql_safe,
                set_mcp_client
            )
            from src.app.core.config import settings
        except ImportError as e1:
            logger.debug(f"从src.app导入失败: {e1}")
            # 如果直接导入失败，尝试使用app导入（如果backend/src在路径中）
            try:
                from app.services.agent.tools import (
                    list_available_tables,
                    get_table_schema,
                    execute_sql_safe,
                    set_mcp_client
                )
                from app.core.config import settings
            except ImportError as e2:
                logger.debug(f"从app导入失败: {e2}")
                raise ImportError(f"无法导入Agent模块: {e2}")
        database_url = getattr(settings, "database_url", None)
        
        if not database_url:
            reporter.add_result(
                "工具调用 - 数据库连接",
                False,
                {
                    "error": "未找到数据库连接字符串",
                    "suggestion": "请检查环境变量 DATABASE_URL 或配置文件"
                }
            )
            return
        
        logger.info(f"数据库URL: {database_url[:50]}...")
        
        # 测试 list_tables
        try:
            logger.info("测试 list_tables...")
            tables_result = list_available_tables.invoke({})
            logger.info(f"list_tables 结果: {tables_result[:200]}...")
            
            reporter.add_result(
                "工具调用 - list_tables",
                True,
                {
                    "result_preview": str(tables_result)[:200],
                    "result_length": len(str(tables_result))
                }
            )
        except Exception as e:
            logger.error(f"list_tables 失败: {e}")
            reporter.add_result(
                "工具调用 - list_tables",
                False,
                {
                    "error": str(e),
                    "suggestion": "检查MCP服务器是否正常运行"
                }
            )
        
        # 测试 get_schema（如果有表的话）
        if "tables_result" in locals() and tables_result:
            try:
                # 尝试解析表名
                import re
                table_match = re.search(r'(\w+)', str(tables_result))
                if table_match:
                    table_name = table_match.group(1)
                    logger.info(f"测试 get_schema (表: {table_name})...")
                    schema_result = get_table_schema.invoke({"table_name": table_name})
                    logger.info(f"get_schema 结果: {schema_result[:200]}...")
                    
                    reporter.add_result(
                        "工具调用 - get_schema",
                        True,
                        {
                            "table_name": table_name,
                            "result_preview": str(schema_result)[:200]
                        }
                    )
            except Exception as e:
                logger.error(f"get_schema 失败: {e}")
                reporter.add_result(
                    "工具调用 - get_schema",
                    False,
                    {"error": str(e)}
                )
        
        # 测试 execute_sql_safe
        try:
            logger.info("测试 execute_sql_safe (简单查询)...")
            sql_result = execute_sql_safe.invoke({
                "sql": "SELECT 1 as test_value",
                "query": "SELECT 1 as test_value"
            })
            logger.info(f"execute_sql_safe 结果: {sql_result[:200]}...")
            
            reporter.add_result(
                "工具调用 - execute_sql_safe",
                True,
                {
                    "sql": "SELECT 1 as test_value",
                    "result_preview": str(sql_result)[:200]
                }
            )
        except Exception as e:
            logger.error(f"execute_sql_safe 失败: {e}")
            reporter.add_result(
                "工具调用 - execute_sql_safe",
                False,
                {"error": str(e)}
            )
    
    except ImportError as e:
        logger.error(f"导入失败: {e}")
        reporter.add_result(
            "工具调用 - 模块导入",
            False,
            {
                "error": f"无法导入Agent模块: {e}",
                "suggestion": "请确保在正确的环境中运行，并且所有依赖已安装"
            }
        )
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
        reporter.add_result(
            "工具调用 - 未知错误",
            False,
            {"error": str(e)}
        )


async def test_agent_simple(reporter: TestReporter):
    """测试2: 简单Agent查询"""
    logger.info("=" * 80)
    logger.info("测试2: 简单Agent查询")
    logger.info("=" * 80)
    
    try:
        try:
            from src.app.services.agent.agent_service import run_agent
            from src.app.core.config import settings
        except ImportError:
            try:
                from app.services.agent.agent_service import run_agent
                from app.core.config import settings
            except ImportError as e:
                raise ImportError(f"无法导入Agent模块: {e}")
        
        database_url = getattr(settings, "database_url", None)
        if not database_url:
            reporter.add_result(
                "Agent查询 - 数据库连接",
                False,
                {"error": "未找到数据库连接字符串"}
            )
            return
        
        # 测试问题1: 列出表
        test_question = "数据库中有哪些表？"
        logger.info(f"测试问题: {test_question}")
        
        try:
            result = await run_agent(
                question=test_question,
                database_url=database_url,
                thread_id="test_session_1",
                verbose=True
            )
            
            logger.info(f"Agent返回结果类型: {type(result)}")
            logger.info(f"Agent返回结果: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}...")
            
            # 检查结果
            has_answer = "answer" in result and result["answer"]
            has_sql = "sql" in result and result.get("sql")
            has_data = "data" in result and result.get("data")
            
            # 检查是否调用了工具
            answer_text = result.get("answer", "")
            has_tool_mention = "表" in answer_text or "table" in answer_text.lower()
            
            reporter.add_result(
                "Agent查询 - 列出表",
                has_answer and (has_sql or has_data or has_tool_mention),
                {
                    "question": test_question,
                    "has_answer": has_answer,
                    "has_sql": bool(has_sql),
                    "has_data": bool(has_data),
                    "answer_preview": answer_text[:200] if has_answer else "无回答",
                    "sql_preview": result.get("sql", "")[:100] if has_sql else "无SQL"
                }
            )
        
        except Exception as e:
            logger.error(f"Agent查询失败: {e}", exc_info=True)
            reporter.add_result(
                "Agent查询 - 列出表",
                False,
                {
                    "error": str(e),
                    "suggestion": "检查Agent服务是否正常运行，MCP服务器是否启动"
                }
            )
    
    except ImportError as e:
        logger.error(f"导入失败: {e}")
        reporter.add_result(
            "Agent查询 - 模块导入",
            False,
            {"error": f"无法导入Agent模块: {e}"}
        )
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
        reporter.add_result(
            "Agent查询 - 未知错误",
            False,
            {"error": str(e)}
        )


async def test_data_consistency(reporter: TestReporter):
    """测试3: 数据一致性验证"""
    logger.info("=" * 80)
    logger.info("测试3: 数据一致性验证")
    logger.info("=" * 80)
    
    try:
        try:
            from src.app.services.agent.tools import execute_sql_safe
            from src.app.services.agent.agent_service import run_agent
            from src.app.core.config import settings
        except ImportError:
            try:
                from app.services.agent.tools import execute_sql_safe
                from app.services.agent.agent_service import run_agent
                from app.core.config import settings
            except ImportError as e:
                raise ImportError(f"无法导入Agent模块: {e}")
        
        database_url = getattr(settings, "database_url", None)
        if not database_url:
            reporter.add_result(
                "数据一致性 - 数据库连接",
                False,
                {"error": "未找到数据库连接字符串"}
            )
            return
        
        # 测试问题: 查询前5条记录
        test_sql = "SELECT * FROM users LIMIT 5"
        test_question = "查询用户表中的前5条记录"
        
        # 1. 手动执行SQL获取真实数据
        try:
            logger.info("手动执行SQL获取真实数据...")
            manual_result = execute_sql_safe.invoke({
                "sql": test_sql,
                "query": test_sql
            })
            
            # 解析结果
            if isinstance(manual_result, str):
                try:
                    manual_data = json.loads(manual_result)
                except:
                    manual_data = manual_result
            else:
                manual_data = manual_result
            
            logger.info(f"手动查询结果: {str(manual_data)[:300]}...")
        
        except Exception as e:
            logger.warning(f"手动SQL执行失败（可能表不存在）: {e}")
            manual_data = None
        
        # 2. 通过Agent执行相同查询
        try:
            logger.info("通过Agent执行查询...")
            agent_result = await run_agent(
                question=test_question,
                database_url=database_url,
                thread_id="test_session_2",
                verbose=True
            )
            
            answer_text = agent_result.get("answer", "")
            agent_sql = agent_result.get("sql", "")
            agent_data = agent_result.get("data")
            
            # 3. 对比数据
            consistency_check = {
                "manual_data_available": manual_data is not None,
                "agent_answer_available": bool(answer_text),
                "agent_sql_available": bool(agent_sql),
                "agent_data_available": bool(agent_data),
                "answer_preview": answer_text[:200] if answer_text else "无回答"
            }
            
            # 检查AI回答中是否包含真实数据
            if manual_data and answer_text:
                # 简单检查：如果手动查询返回了数据，检查AI回答中是否提到了这些数据
                manual_str = str(manual_data)
                # 提取一些关键信息（如果有的话）
                if isinstance(manual_data, list) and len(manual_data) > 0:
                    first_record = manual_data[0]
                    if isinstance(first_record, dict):
                        # 检查AI回答中是否包含第一条记录的某些值
                        for key, value in list(first_record.items())[:3]:  # 只检查前3个字段
                            if str(value) in answer_text:
                                consistency_check[f"contains_{key}"] = True
                                break
            
            reporter.add_result(
                "数据一致性 - 查询对比",
                consistency_check.get("agent_answer_available", False),
                consistency_check
            )
        
        except Exception as e:
            logger.error(f"Agent查询失败: {e}", exc_info=True)
            reporter.add_result(
                "数据一致性 - Agent查询",
                False,
                {"error": str(e)}
            )
    
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
        reporter.add_result(
            "数据一致性 - 未知错误",
            False,
            {"error": str(e)}
        )


async def run_all_tests():
    """运行所有测试"""
    reporter = TestReporter()
    
    logger.info("开始执行AI助手编造数据问题诊断测试...")
    logger.info("")
    
    # 运行测试
    await test_tool_calls(reporter)
    await test_agent_simple(reporter)
    await test_data_consistency(reporter)
    
    # 生成报告
    report = reporter.generate_report()
    print("\n" + report)
    
    # 保存报告
    report_dir = project_root / "docs" / "test_reports"
    report_dir.mkdir(exist_ok=True)
    report_file = report_dir / f"ai_hallucination_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    reporter.save_report(str(report_file))
    
    logger.info(f"\n测试完成！报告已保存到: {report_file}")


async def main():
    """主函数"""
    import sys as sys_module
    if len(sys_module.argv) > 1:
        test_name = sys_module.argv[1]
        reporter = TestReporter()
        
        if test_name == "tool_calls":
            await test_tool_calls(reporter)
        elif test_name == "agent_simple":
            await test_agent_simple(reporter)
        elif test_name == "data_consistency":
            await test_data_consistency(reporter)
        elif test_name == "all":
            await run_all_tests()
            return
        else:
            print(f"未知测试名称: {test_name}")
            print("可用测试: tool_calls, agent_simple, data_consistency, all")
            return
        
        # 生成报告
        report = reporter.generate_report()
        try:
            print("\n" + report)
        except UnicodeEncodeError:
            # Windows编码问题，使用UTF-8
            import sys
            sys.stdout.reconfigure(encoding='utf-8')
            print("\n" + report)
        
        # 保存报告
        report_dir = project_root / "docs" / "test_reports"
        report_dir.mkdir(exist_ok=True)
        report_file = report_dir / f"ai_hallucination_test_{test_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        reporter.save_report(str(report_file))
    else:
        await run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())

