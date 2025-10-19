"""
扩展工具集 - 更多实用工具实现
增强 Agent 的能力范围
"""
import os
import json
import base64
import hashlib
import uuid
import random
import string
import csv
import re
from typing import Any, Dict, List, Optional
from datetime import datetime
import httpx
from .tool_base import Tool, ToolOutput, ToolCategory


class FileReaderTool(Tool):
    """文件读取工具 - 读取本地文件内容"""
    
    def _get_name(self) -> str:
        return "read_file"
    
    def _get_description(self) -> str:
        return "读取本地文件的内容。支持文本文件（txt、json、csv、md等）。返回文件内容或错误信息。"
    
    def _get_category(self) -> ToolCategory:
        return ToolCategory.FILE_OPERATION
    
    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "文件路径"
                },
                "encoding": {
                    "type": "string",
                    "description": "文件编码",
                    "default": "utf-8"
                }
            },
            "required": ["file_path"]
        }
    
    async def _execute(self, file_path: str, encoding: str = "utf-8") -> ToolOutput:
        """读取文件"""
        try:
            if not os.path.exists(file_path):
                return ToolOutput(
                    success=False,
                    result=None,
                    error=f"文件不存在: {file_path}"
                )
            
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            
            # 获取文件信息
            file_size = os.path.getsize(file_path)
            file_ext = os.path.splitext(file_path)[1]
            
            return ToolOutput(
                success=True,
                result=content,
                metadata={
                    "file_path": file_path,
                    "file_size": file_size,
                    "file_extension": file_ext,
                    "encoding": encoding
                }
            )
            
        except Exception as e:
            return ToolOutput(
                success=False,
                result=None,
                error=f"读取文件失败: {str(e)}"
            )


class FileWriterTool(Tool):
    """文件写入工具 - 写入内容到文件"""
    
    def _get_name(self) -> str:
        return "write_file"
    
    def _get_description(self) -> str:
        return "将内容写入到文件中。可以创建新文件或覆盖现有文件。支持文本内容的写入。"
    
    def _get_category(self) -> ToolCategory:
        return ToolCategory.FILE_OPERATION
    
    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "文件路径"
                },
                "content": {
                    "type": "string",
                    "description": "要写入的内容"
                },
                "mode": {
                    "type": "string",
                    "description": "写入模式：'w'(覆盖)、'a'(追加)",
                    "enum": ["w", "a"],
                    "default": "w"
                },
                "encoding": {
                    "type": "string",
                    "description": "文件编码",
                    "default": "utf-8"
                }
            },
            "required": ["file_path", "content"]
        }
    
    async def _execute(
        self, 
        file_path: str, 
        content: str, 
        mode: str = "w",
        encoding: str = "utf-8"
    ) -> ToolOutput:
        """写入文件"""
        try:
            # 确保目录存在
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            
            with open(file_path, mode, encoding=encoding) as f:
                f.write(content)
            
            file_size = os.path.getsize(file_path)
            
            return ToolOutput(
                success=True,
                result=f"成功写入 {file_size} 字节到 {file_path}",
                metadata={
                    "file_path": file_path,
                    "file_size": file_size,
                    "mode": mode
                }
            )
            
        except Exception as e:
            return ToolOutput(
                success=False,
                result=None,
                error=f"写入文件失败: {str(e)}"
            )


class CSVProcessorTool(Tool):
    """CSV处理工具 - 读取和解析CSV文件"""
    
    def _get_name(self) -> str:
        return "process_csv"
    
    def _get_description(self) -> str:
        return "处理CSV文件。可以读取CSV内容、统计行数、提取列、过滤数据等操作。"
    
    def _get_category(self) -> ToolCategory:
        return ToolCategory.DATA_ANALYSIS
    
    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "CSV文件路径"
                },
                "operation": {
                    "type": "string",
                    "description": "操作类型：'read'(读取)、'stats'(统计)、'columns'(列名)",
                    "enum": ["read", "stats", "columns"],
                    "default": "read"
                },
                "max_rows": {
                    "type": "integer",
                    "description": "最大读取行数",
                    "default": 100
                }
            },
            "required": ["file_path"]
        }
    
    async def _execute(
        self, 
        file_path: str, 
        operation: str = "read",
        max_rows: int = 100
    ) -> ToolOutput:
        """处理CSV"""
        try:
            if not os.path.exists(file_path):
                return ToolOutput(
                    success=False,
                    result=None,
                    error=f"文件不存在: {file_path}"
                )
            
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            if operation == "columns":
                columns = list(rows[0].keys()) if rows else []
                result = {
                    "columns": columns,
                    "column_count": len(columns)
                }
            
            elif operation == "stats":
                result = {
                    "total_rows": len(rows),
                    "columns": list(rows[0].keys()) if rows else [],
                    "column_count": len(rows[0].keys()) if rows else 0
                }
            
            else:  # read
                result = {
                    "rows": rows[:max_rows],
                    "total_rows": len(rows),
                    "returned_rows": min(len(rows), max_rows)
                }
            
            return ToolOutput(
                success=True,
                result=result,
                metadata={
                    "file_path": file_path,
                    "operation": operation
                }
            )
            
        except Exception as e:
            return ToolOutput(
                success=False,
                result=None,
                error=f"CSV处理失败: {str(e)}"
            )


class HTTPRequestTool(Tool):
    """HTTP请求工具 - 发送HTTP请求"""
    
    def _get_name(self) -> str:
        return "http_request"
    
    def _get_description(self) -> str:
        return "发送HTTP请求到指定URL。支持GET、POST等方法，可以设置headers和body。用于API调用和数据获取。"
    
    def _get_category(self) -> ToolCategory:
        return ToolCategory.WEB_SCRAPING
    
    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "请求的URL地址"
                },
                "method": {
                    "type": "string",
                    "description": "HTTP方法",
                    "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                    "default": "GET"
                },
                "headers": {
                    "type": "object",
                    "description": "请求头（可选）",
                    "default": {}
                },
                "body": {
                    "type": "object",
                    "description": "请求体（可选，JSON格式）",
                    "default": {}
                }
            },
            "required": ["url"]
        }
    
    async def _execute(
        self,
        url: str,
        method: str = "GET",
        headers: Dict[str, str] = None,
        body: Dict[str, Any] = None
    ) -> ToolOutput:
        """发送HTTP请求"""
        try:
            headers = headers or {}
            body = body or {}
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method == "GET":
                    response = await client.get(url, headers=headers)
                elif method == "POST":
                    response = await client.post(url, headers=headers, json=body)
                elif method == "PUT":
                    response = await client.put(url, headers=headers, json=body)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers)
                elif method == "PATCH":
                    response = await client.patch(url, headers=headers, json=body)
                else:
                    return ToolOutput(
                        success=False,
                        result=None,
                        error=f"不支持的HTTP方法: {method}"
                    )
                
                # 尝试解析JSON响应
                try:
                    response_data = response.json()
                except:
                    response_data = response.text
                
                result = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": response_data
                }
                
                return ToolOutput(
                    success=True,
                    result=result,
                    metadata={
                        "url": url,
                        "method": method,
                        "status_code": response.status_code
                    }
                )
                
        except Exception as e:
            return ToolOutput(
                success=False,
                result=None,
                error=f"HTTP请求失败: {str(e)}"
            )


class DataConverterTool(Tool):
    """数据格式转换工具 - 转换不同数据格式"""
    
    def _get_name(self) -> str:
        return "convert_data_format"
    
    def _get_description(self) -> str:
        return "在不同数据格式之间转换。支持JSON、CSV、XML等格式的相互转换。"
    
    def _get_category(self) -> ToolCategory:
        return ToolCategory.DATA_ANALYSIS
    
    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "data": {
                    "type": "string",
                    "description": "要转换的数据（字符串格式）"
                },
                "from_format": {
                    "type": "string",
                    "description": "源格式",
                    "enum": ["json", "csv"]
                },
                "to_format": {
                    "type": "string",
                    "description": "目标格式",
                    "enum": ["json", "csv", "markdown"]
                }
            },
            "required": ["data", "from_format", "to_format"]
        }
    
    async def _execute(
        self,
        data: str,
        from_format: str,
        to_format: str
    ) -> ToolOutput:
        """转换数据格式"""
        try:
            # 解析源格式
            if from_format == "json":
                parsed_data = json.loads(data)
            elif from_format == "csv":
                lines = data.strip().split('\n')
                reader = csv.DictReader(lines)
                parsed_data = list(reader)
            else:
                return ToolOutput(
                    success=False,
                    result=None,
                    error=f"不支持的源格式: {from_format}"
                )
            
            # 转换到目标格式
            if to_format == "json":
                result = json.dumps(parsed_data, ensure_ascii=False, indent=2)
            
            elif to_format == "csv":
                if isinstance(parsed_data, list) and len(parsed_data) > 0:
                    keys = parsed_data[0].keys()
                    lines = [','.join(keys)]
                    for item in parsed_data:
                        lines.append(','.join(str(item.get(k, '')) for k in keys))
                    result = '\n'.join(lines)
                else:
                    return ToolOutput(
                        success=False,
                        result=None,
                        error="无法转换为CSV：数据不是列表格式"
                    )
            
            elif to_format == "markdown":
                if isinstance(parsed_data, list) and len(parsed_data) > 0:
                    keys = list(parsed_data[0].keys())
                    lines = []
                    # 表头
                    lines.append('| ' + ' | '.join(keys) + ' |')
                    lines.append('| ' + ' | '.join(['---'] * len(keys)) + ' |')
                    # 数据行
                    for item in parsed_data:
                        lines.append('| ' + ' | '.join(str(item.get(k, '')) for k in keys) + ' |')
                    result = '\n'.join(lines)
                else:
                    result = "```json\n" + json.dumps(parsed_data, ensure_ascii=False, indent=2) + "\n```"
            
            else:
                return ToolOutput(
                    success=False,
                    result=None,
                    error=f"不支持的目标格式: {to_format}"
                )
            
            return ToolOutput(
                success=True,
                result=result,
                metadata={
                    "from_format": from_format,
                    "to_format": to_format
                }
            )
            
        except Exception as e:
            return ToolOutput(
                success=False,
                result=None,
                error=f"格式转换失败: {str(e)}"
            )


class RandomGeneratorTool(Tool):
    """随机生成器工具 - 生成各种随机数据"""
    
    def _get_name(self) -> str:
        return "generate_random"
    
    def _get_description(self) -> str:
        return "生成随机数据。支持随机数、随机字符串、UUID、密码等的生成。"
    
    def _get_category(self) -> ToolCategory:
        return ToolCategory.UTILITY
    
    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "description": "生成类型",
                    "enum": ["number", "string", "uuid", "password"]
                },
                "length": {
                    "type": "integer",
                    "description": "长度（对于string和password）",
                    "default": 12
                },
                "min": {
                    "type": "integer",
                    "description": "最小值（对于number）",
                    "default": 0
                },
                "max": {
                    "type": "integer",
                    "description": "最大值（对于number）",
                    "default": 100
                }
            },
            "required": ["type"]
        }
    
    async def _execute(
        self,
        type: str,
        length: int = 12,
        min: int = 0,
        max: int = 100
    ) -> ToolOutput:
        """生成随机数据"""
        try:
            if type == "number":
                result = random.randint(min, max)
            
            elif type == "string":
                chars = string.ascii_letters + string.digits
                result = ''.join(random.choice(chars) for _ in range(length))
            
            elif type == "uuid":
                result = str(uuid.uuid4())
            
            elif type == "password":
                # 包含大小写字母、数字和特殊字符
                chars = string.ascii_letters + string.digits + "!@#$%^&*"
                result = ''.join(random.choice(chars) for _ in range(length))
            
            else:
                return ToolOutput(
                    success=False,
                    result=None,
                    error=f"不支持的生成类型: {type}"
                )
            
            return ToolOutput(
                success=True,
                result=result,
                metadata={
                    "type": type,
                    "length": length if type in ["string", "password"] else None
                }
            )
            
        except Exception as e:
            return ToolOutput(
                success=False,
                result=None,
                error=f"随机生成失败: {str(e)}"
            )


class EncodingTool(Tool):
    """编码工具 - Base64编解码和Hash计算"""
    
    def _get_name(self) -> str:
        return "encode_decode"
    
    def _get_description(self) -> str:
        return "编码和解码工具。支持Base64编解码、MD5/SHA256哈希计算等操作。"
    
    def _get_category(self) -> ToolCategory:
        return ToolCategory.UTILITY
    
    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "操作类型",
                    "enum": ["base64_encode", "base64_decode", "md5", "sha256"]
                },
                "text": {
                    "type": "string",
                    "description": "要处理的文本"
                }
            },
            "required": ["operation", "text"]
        }
    
    async def _execute(self, operation: str, text: str) -> ToolOutput:
        """执行编码操作"""
        try:
            if operation == "base64_encode":
                encoded = base64.b64encode(text.encode('utf-8')).decode('utf-8')
                result = encoded
            
            elif operation == "base64_decode":
                decoded = base64.b64decode(text.encode('utf-8')).decode('utf-8')
                result = decoded
            
            elif operation == "md5":
                hash_obj = hashlib.md5(text.encode('utf-8'))
                result = hash_obj.hexdigest()
            
            elif operation == "sha256":
                hash_obj = hashlib.sha256(text.encode('utf-8'))
                result = hash_obj.hexdigest()
            
            else:
                return ToolOutput(
                    success=False,
                    result=None,
                    error=f"不支持的操作: {operation}"
                )
            
            return ToolOutput(
                success=True,
                result=result,
                metadata={
                    "operation": operation,
                    "input_length": len(text)
                }
            )
            
        except Exception as e:
            return ToolOutput(
                success=False,
                result=None,
                error=f"编码操作失败: {str(e)}"
            )


class URLExtractorTool(Tool):
    """URL提取工具 - 从文本中提取URL"""
    
    def _get_name(self) -> str:
        return "extract_urls"
    
    def _get_description(self) -> str:
        return "从文本中提取所有URL链接。可以识别http、https等各种URL格式。"
    
    def _get_category(self) -> ToolCategory:
        return ToolCategory.DATA_ANALYSIS
    
    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "要从中提取URL的文本"
                }
            },
            "required": ["text"]
        }
    
    async def _execute(self, text: str) -> ToolOutput:
        """提取URL"""
        try:
            # URL正则表达式
            url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
            urls = re.findall(url_pattern, text)
            
            # 去重
            unique_urls = list(set(urls))
            
            result = {
                "urls": unique_urls,
                "count": len(unique_urls)
            }
            
            return ToolOutput(
                success=True,
                result=result,
                metadata={
                    "total_found": len(urls),
                    "unique_count": len(unique_urls)
                }
            )
            
        except Exception as e:
            return ToolOutput(
                success=False,
                result=None,
                error=f"URL提取失败: {str(e)}"
            )


class EmailValidatorTool(Tool):
    """邮箱验证工具 - 验证邮箱格式是否正确"""
    
    def _get_name(self) -> str:
        return "validate_email"
    
    def _get_description(self) -> str:
        return "验证邮箱地址格式是否正确。返回验证结果和详细信息。"
    
    def _get_category(self) -> ToolCategory:
        return ToolCategory.UTILITY
    
    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "要验证的邮箱地址"
                }
            },
            "required": ["email"]
        }
    
    async def _execute(self, email: str) -> ToolOutput:
        """验证邮箱"""
        try:
            # 邮箱正则表达式
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            is_valid = bool(re.match(email_pattern, email))
            
            result = {
                "email": email,
                "is_valid": is_valid,
                "domain": email.split('@')[1] if '@' in email else None,
                "username": email.split('@')[0] if '@' in email else None
            }
            
            return ToolOutput(
                success=True,
                result=result,
                metadata={"is_valid": is_valid}
            )
            
        except Exception as e:
            return ToolOutput(
                success=False,
                result=None,
                error=f"邮箱验证失败: {str(e)}"
            )


class DataStatisticsTool(Tool):
    """数据统计工具 - 对数值列表进行统计分析"""
    
    def _get_name(self) -> str:
        return "calculate_statistics"
    
    def _get_description(self) -> str:
        return "对数值列表进行统计分析。计算平均值、中位数、标准差、最大值、最小值等统计指标。"
    
    def _get_category(self) -> ToolCategory:
        return ToolCategory.DATA_ANALYSIS
    
    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "numbers": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "数值列表"
                }
            },
            "required": ["numbers"]
        }
    
    async def _execute(self, numbers: List[float]) -> ToolOutput:
        """计算统计数据"""
        try:
            if not numbers:
                return ToolOutput(
                    success=False,
                    result=None,
                    error="数值列表为空"
                )
            
            sorted_numbers = sorted(numbers)
            n = len(numbers)
            
            # 计算统计指标
            mean = sum(numbers) / n
            median = sorted_numbers[n // 2] if n % 2 != 0 else (sorted_numbers[n // 2 - 1] + sorted_numbers[n // 2]) / 2
            
            # 标准差
            variance = sum((x - mean) ** 2 for x in numbers) / n
            std_dev = variance ** 0.5
            
            result = {
                "count": n,
                "sum": sum(numbers),
                "mean": round(mean, 2),
                "median": median,
                "std_dev": round(std_dev, 2),
                "min": min(numbers),
                "max": max(numbers),
                "range": max(numbers) - min(numbers)
            }
            
            return ToolOutput(
                success=True,
                result=result,
                metadata={"data_points": n}
            )
            
        except Exception as e:
            return ToolOutput(
                success=False,
                result=None,
                error=f"统计计算失败: {str(e)}"
            )