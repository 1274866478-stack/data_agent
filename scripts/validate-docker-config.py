#!/usr/bin/env python3
"""
 =============================================================================
 Data Agent V4 - Docker Environment Configuration Validator
 =============================================================================

 验证Docker环境配置的完整性和正确性
 Validate Docker environment configuration integrity and correctness

 使用方法 / Usage:
     python scripts/validate-docker-config.py
     python scripts/validate-docker-config.py --fix
     python scripts/validate-docker-config.py --env-file .env
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional

class Colors:
    """控制台颜色"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

class DockerConfigValidator:
    """Docker配置验证器"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.errors = []
        self.warnings = []
        self.success_count = 0

    def print_header(self):
        """打印标题"""
        print(f"{Colors.BOLD}{Colors.CYAN}")
        print("=" * 80)
        print(" Data Agent V4 - Docker环境配置验证器")
        print(" Docker Environment Configuration Validator")
        print("=" * 80)
        print(f"{Colors.END}")

    def print_result(self, success: bool, message: str, details: str = ""):
        """打印结果"""
        if success:
            print(f"{Colors.GREEN}✅ {message}{Colors.END}")
            self.success_count += 1
        else:
            print(f"{Colors.RED}❌ {message}{Colors.END}")
            self.errors.append(message)

        if details:
            print(f"   {Colors.YELLOW}{details}{Colors.END}")

    def print_warning(self, message: str):
        """打印警告"""
        print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")
        self.warnings.append(message)

    def validate_project_structure(self) -> bool:
        """验证项目结构"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}验证项目结构 / Validating Project Structure{Colors.END}")

        required_dirs = ['frontend', 'backend', 'scripts', 'docs']
        required_files = [
            'docker-compose.yml',
            '.env.example',
            'frontend/Dockerfile',
            'backend/Dockerfile',
            'backend/requirements.txt',
            'frontend/package.json',
            'backend/scripts/init-db.sql'
        ]

        all_valid = True

        # 验证目录
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists() and dir_path.is_dir():
                self.print_result(True, f"目录存在: {dir_name}/")
            else:
                self.print_result(False, f"目录缺失: {dir_name}/")
                all_valid = False

        # 验证文件
        for file_name in required_files:
            file_path = self.project_root / file_name
            if file_path.exists() and file_path.is_file():
                self.print_result(True, f"文件存在: {file_name}")
            else:
                self.print_result(False, f"文件缺失: {file_name}")
                all_valid = False

        return all_valid

    def validate_docker_compose(self) -> bool:
        """验证docker-compose.yml配置"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}验证Docker Compose配置 / Validating Docker Compose{Colors.END}")

        compose_file = self.project_root / 'docker-compose.yml'

        if not compose_file.exists():
            self.print_result(False, "docker-compose.yml文件不存在")
            return False

        try:
            # 尝试解析docker-compose.yml
            result = subprocess.run(
                ['docker', 'compose', '-f', str(compose_file), 'config', '--quiet'],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                self.print_result(True, "docker-compose.yml语法正确")
            else:
                self.print_result(False, "docker-compose.yml语法错误", result.stderr)
                return False

        except FileNotFoundError:
            self.print_warning("Docker未安装或不在PATH中")
            return False

        # 检查服务配置
        try:
            result = subprocess.run(
                ['docker', 'compose', '-f', str(compose_file), 'config'],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                config_content = result.stdout

                # 检查必需的服务
                required_services = ['frontend', 'backend', 'db', 'storage', 'vector_db']
                for service in required_services:
                    if f"{service}:" in config_content:
                        self.print_result(True, f"服务配置存在: {service}")
                    else:
                        self.print_result(False, f"服务配置缺失: {service}")

        except Exception as e:
            self.print_warning(f"无法分析docker-compose配置: {e}")

        return True

    def validate_env_file(self, env_file: str = '.env') -> bool:
        """验证环境变量文件"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}🔧 验证环境变量配置 / Validating Environment Variables{Colors.END}")

        # 首先检查.env.example
        env_example = self.project_root / '.env.example'
        if not env_example.exists():
            self.print_result(False, ".env.example文件不存在")
            return False
        else:
            self.print_result(True, ".env.example文件存在")

        # 检查实际.env文件
        env_path = self.project_root / env_file
        if not env_path.exists():
            self.print_warning(f"{env_file}文件不存在，请复制.env.example并配置")
            return False

        # 读取环境变量
        env_vars = {}
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        except Exception as e:
            self.print_result(False, f"读取{env_file}文件失败", str(e))
            return False

        # 检查必需的环境变量
        required_vars = [
            'ZHIPUAI_API_KEY',
            'DATABASE_URL',
            'SECRET_KEY'
        ]

        all_valid = True
        for var in required_vars:
            if var in env_vars and env_vars[var] and not env_vars[var].startswith('your_'):
                self.print_result(True, f"环境变量已配置: {var}")
            else:
                self.print_result(False, f"环境变量未配置或使用默认值: {var}")
                all_valid = False

        # 检查ZHIPUAI_API_KEY格式
        if 'ZHIPUAI_API_KEY' in env_vars:
            api_key = env_vars['ZHIPUAI_API_KEY']
            if api_key.startswith('your_') or len(api_key) < 10:
                self.print_warning("ZHIPUAI_API_KEY看起来无效，请配置真实的API密钥")
            else:
                self.print_result(True, "ZHIPUAI_API_KEY格式看起来正确")

        return all_valid

    def validate_docker_files(self) -> bool:
        """验证Dockerfile文件"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}📦 验证Dockerfile配置 / Validating Dockerfiles{Colors.END}")

        dockerfiles = [
            ('frontend/Dockerfile', '前端'),
            ('backend/Dockerfile', '后端')
        ]

        all_valid = True

        for dockerfile_path, service_name in dockerfiles:
            file_path = self.project_root / dockerfile_path

            if not file_path.exists():
                self.print_result(False, f"{service_name}Dockerfile不存在: {dockerfile_path}")
                all_valid = False
                continue

            # 检查Dockerfile内容
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 检查基本指令
                if 'FROM' in content:
                    self.print_result(True, f"{service_name}Dockerfile包含FROM指令")
                else:
                    self.print_result(False, f"{service_name}Dockerfile缺少FROM指令")
                    all_valid = False

                if 'EXPOSE' in content:
                    self.print_result(True, f"{service_name}Dockerfile包含EXPOSE指令")
                else:
                    self.print_warning(f"{service_name}Dockerfile缺少EXPOSE指令")

                if 'HEALTHCHECK' in content:
                    self.print_result(True, f"{service_name}Dockerfile包含HEALTHCHECK")
                else:
                    self.print_warning(f"{service_name}Dockerfile缺少HEALTHCHECK")

            except Exception as e:
                self.print_result(False, f"读取{service_name}Dockerfile失败", str(e))
                all_valid = False

        return all_valid

    def validate_database_init(self) -> bool:
        """验证数据库初始化脚本"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}🗄️ 验证数据库初始化脚本 / Validating Database Init Script{Colors.END}")

        init_script = self.project_root / 'backend' / 'scripts' / 'init-db.sql'

        if not init_script.exists():
            self.print_result(False, "数据库初始化脚本不存在")
            return False

        try:
            with open(init_script, 'r', encoding='utf-8') as f:
                content = f.read()

            # 检查关键SQL语句
            required_statements = [
                'CREATE EXTENSION',
                'CREATE TABLE tenants',
                'CREATE TABLE users',
                'CREATE TABLE data_source_connections',
                'CREATE TABLE knowledge_documents'
            ]

            all_valid = True
            for stmt in required_statements:
                if stmt in content:
                    self.print_result(True, f"包含必需语句: {stmt}")
                else:
                    self.print_result(False, f"缺少必需语句: {stmt}")
                    all_valid = False

            return all_valid

        except Exception as e:
            self.print_result(False, "读取数据库初始化脚本失败", str(e))
            return False

    def check_docker_daemon(self) -> bool:
        """检查Docker守护进程"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}🐋 检查Docker环境 / Checking Docker Environment{Colors.END}")

        try:
            # 检查Docker是否运行
            result = subprocess.run(
                ['docker', 'info'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                self.print_result(True, "Docker守护进程运行正常")

                # 获取Docker版本
                version_result = subprocess.run(
                    ['docker', '--version'],
                    capture_output=True,
                    text=True
                )

                if version_result.returncode == 0:
                    version = version_result.stdout.strip()
                    print(f"   {Colors.CYAN}版本: {version}{Colors.END}")

                return True
            else:
                self.print_result(False, "Docker守护进程未运行")
                return False

        except FileNotFoundError:
            self.print_result(False, "Docker未安装或不在PATH中")
            return False
        except subprocess.TimeoutExpired:
            self.print_result(False, "Docker命令超时")
            return False
        except Exception as e:
            self.print_result(False, f"检查Docker时发生错误", str(e))
            return False

    def generate_summary(self):
        """生成验证摘要"""
        print(f"\n{Colors.BOLD}{Colors.MAGENTA}📊 验证摘要 / Validation Summary{Colors.END}")
        print("=" * 80)

        print(f"{Colors.GREEN}✅ 成功项: {self.success_count}{Colors.END}")
        print(f"{Colors.RED}❌ 错误项: {len(self.errors)}{Colors.END}")
        print(f"{Colors.YELLOW}⚠️ 警告项: {len(self.warnings)}{Colors.END}")

        if self.errors:
            print(f"\n{Colors.RED}错误详情:{Colors.END}")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")

        if self.warnings:
            print(f"\n{Colors.YELLOW}警告详情:{Colors.END}")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")

        # 总体状态
        if not self.errors:
            print(f"\n{Colors.BOLD}{Colors.GREEN}🎉 配置验证通过！Docker环境配置正确。{Colors.END}")
            print(f"{Colors.CYAN}可以运行以下命令启动环境:{Colors.END}")
            print(f"   docker compose up -d")
            return True
        else:
            print(f"\n{Colors.BOLD}{Colors.RED}❌ 配置验证失败！请修复上述错误后重试。{Colors.END}")
            return False

    def fix_common_issues(self):
        """修复常见问题"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}🔧 尝试修复常见问题 / Attempting to Fix Common Issues{Colors.END}")

        # 创建.env文件如果不存在
        env_file = self.project_root / '.env'
        env_example = self.project_root / '.env.example'

        if not env_file.exists() and env_example.exists():
            try:
                import shutil
                shutil.copy2(env_example, env_file)
                self.print_result(True, "已创建.env文件（从.env.example复制）")
                print(f"   {Colors.YELLOW}请编辑.env文件并配置真实的API密钥和密码{Colors.END}")
            except Exception as e:
                self.print_result(False, "创建.env文件失败", str(e))

        # 创建必要的目录
        required_dirs = [
            'backend/logs',
            'backend/uploads',
            'backend/temp',
            'frontend/logs'
        ]

        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                self.print_result(True, f"已创建目录: {dir_name}")
            except Exception as e:
                self.print_warning(f"创建目录失败 {dir_name}: {e}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Data Agent V4 Docker配置验证器')
    parser.add_argument('--env-file', default='.env', help='环境变量文件路径')
    parser.add_argument('--fix', action='store_true', help='尝试修复常见问题')
    parser.add_argument('--project-root', help='项目根目录路径')

    args = parser.parse_args()

    # 初始化验证器
    project_root = Path(args.project_root) if args.project_root else Path(__file__).parent.parent
    validator = DockerConfigValidator(project_root)

    # 打印标题
    validator.print_header()

    # 执行验证
    validations = [
        validator.validate_project_structure(),
        validator.validate_docker_compose(),
        validator.validate_env_file(args.env_file),
        validator.validate_docker_files(),
        validator.validate_database_init(),
        validator.check_docker_daemon()
    ]

    # 尝试修复问题
    if args.fix:
        validator.fix_common_issues()

    # 生成摘要
    success = validator.generate_summary()

    # 退出码
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()