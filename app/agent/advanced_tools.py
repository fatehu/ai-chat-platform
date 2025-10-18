"""
高级工具集 - 更实用的工具实现
"""
import json
import re
from typing import Any, Dict, List
from datetime import datetime, timedelta
import httpx
from .tool_base import Tool, ToolOutput, ToolCategory


class WeatherTool(Tool):
    """天气查询工具 - 使用开放API获取天气信息"""
    
    def _get_name(self) -> str:
        return "get_weather"
    
    def _get_description(self) -> str:
        return "获取指定城市的天气信息。可以查询当前天气、温度、湿度等信息。"
    
    def _get_category(self) -> ToolCategory:
        return ToolCategory.WEB_SCRAPING
    
    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称，例如：北京、上海、广州"
                }
            },
            "required": ["city"]
        }
    
    async def _execute(self, city: str) -> ToolOutput:
        """获取天气信息"""
        try:
            # 使用wttr.in免费API（实际项目中应使用更可靠的API）
            url = f"https://wttr.in/{city}?format=j1"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    current = data.get("current_condition", [{}])[0]
                    
                    weather_info = {
                        "城市": city,
                        "温度": f"{current.get('temp_C', 'N/A')}°C",
                        "天气": current.get('weatherDesc', [{}])[0].get('value', 'N/A'),
                        "湿度": f"{current.get('humidity', 'N/A')}%",
                        "风速": f"{current.get('windspeedKmph', 'N/A')} km/h",
                        "查询时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    return ToolOutput(
                        success=True,
                        result=weather_info,
                        metadata={"source": "wttr.in"}
                    )
                else:
                    return ToolOutput(
                        success=False,
                        result=None,
                        error=f"无法获取天气信息，HTTP状态码: {response.status_code}"
                    )
                    
        except Exception as e:
            return ToolOutput(
                success=False,
                result=None,
                error=f"天气查询失败: {str(e)}"
            )


class TextAnalysisTool(Tool):
    """文本分析工具 - 统计文本特征"""
    
    def _get_name(self) -> str:
        return "analyze_text"
    
    def _get_description(self) -> str:
        return "分析文本内容，统计字数、词频、句子数等信息。适用于文本分析和内容审查。"
    
    def _get_category(self) -> ToolCategory:
        return ToolCategory.DATA_ANALYSIS
    
    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "要分析的文本内容"
                }
            },
            "required": ["text"]
        }
    
    async def _execute(self, text: str) -> ToolOutput:
        """分析文本"""
        try:
            # 基础统计
            char_count = len(text)
            word_count = len(text.split())
            
            # 句子统计（简单实现）
            sentences = re.split(r'[。！？.!?]+', text)
            sentence_count = len([s for s in sentences if s.strip()])
            
            # 段落统计
            paragraphs = text.split('\n\n')
            paragraph_count = len([p for p in paragraphs if p.strip()])
            
            # 词频统计（前10个）
            words = text.split()
            word_freq = {}
            for word in words:
                word = word.strip('，。！？,.')
                if len(word) > 1:  # 忽略单字
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
            
            analysis = {
                "字符数": char_count,
                "词数": word_count,
                "句子数": sentence_count,
                "段落数": paragraph_count,
                "平均句长": round(char_count / sentence_count, 2) if sentence_count > 0 else 0,
                "高频词": [{"词": w, "频次": f} for w, f in top_words]
            }
            
            return ToolOutput(
                success=True,
                result=analysis,
                metadata={"text_length": char_count}
            )
            
        except Exception as e:
            return ToolOutput(
                success=False,
                result=None,
                error=f"文本分析失败: {str(e)}"
            )


class JSONParserTool(Tool):
    """JSON解析工具 - 解析和提取JSON数据"""
    
    def _get_name(self) -> str:
        return "parse_json"
    
    def _get_description(self) -> str:
        return "解析JSON字符串并提取指定字段。可以处理复杂的JSON结构，支持路径查询。"
    
    def _get_category(self) -> ToolCategory:
        return ToolCategory.DATA_ANALYSIS
    
    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "json_string": {
                    "type": "string",
                    "description": "JSON格式的字符串"
                },
                "path": {
                    "type": "string",
                    "description": "要提取的字段路径，例如：'user.name' 或 'items[0].price'",
                    "default": ""
                }
            },
            "required": ["json_string"]
        }
    
    async def _execute(self, json_string: str, path: str = "") -> ToolOutput:
        """解析JSON"""
        try:
            # 解析JSON
            data = json.loads(json_string)
            
            # 如果没有指定路径，返回整个对象
            if not path:
                return ToolOutput(
                    success=True,
                    result=data,
                    metadata={"parsed": True, "type": type(data).__name__}
                )
            
            # 按路径提取数据
            parts = path.replace('[', '.').replace(']', '').split('.')
            result = data
            
            for part in parts:
                if part.isdigit():
                    result = result[int(part)]
                else:
                    result = result[part]
            
            return ToolOutput(
                success=True,
                result=result,
                metadata={"path": path, "extracted": True}
            )
            
        except json.JSONDecodeError as e:
            return ToolOutput(
                success=False,
                result=None,
                error=f"JSON解析失败: {str(e)}"
            )
        except (KeyError, IndexError, TypeError) as e:
            return ToolOutput(
                success=False,
                result=None,
                error=f"路径提取失败: {str(e)}"
            )
        except Exception as e:
            return ToolOutput(
                success=False,
                result=None,
                error=f"处理失败: {str(e)}"
            )


class TimerTool(Tool):
    """定时器工具 - 计算时间间隔和未来时间"""
    
    def _get_name(self) -> str:
        return "time_calculator"
    
    def _get_description(self) -> str:
        return "计算时间相关信息。可以计算未来/过去的时间、时间间隔、日期差等。"
    
    def _get_category(self) -> ToolCategory:
        return ToolCategory.UTILITY
    
    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "操作类型：'add'(加时间)、'subtract'(减时间)、'diff'(计算差值)",
                    "enum": ["add", "subtract", "diff"]
                },
                "amount": {
                    "type": "integer",
                    "description": "时间数量"
                },
                "unit": {
                    "type": "string",
                    "description": "时间单位：'days'、'hours'、'minutes'",
                    "enum": ["days", "hours", "minutes"]
                }
            },
            "required": ["operation", "amount", "unit"]
        }
    
    async def _execute(self, operation: str, amount: int, unit: str) -> ToolOutput:
        """计算时间"""
        try:
            now = datetime.now()
            
            # 构建时间增量
            if unit == "days":
                delta = timedelta(days=amount)
            elif unit == "hours":
                delta = timedelta(hours=amount)
            elif unit == "minutes":
                delta = timedelta(minutes=amount)
            else:
                return ToolOutput(
                    success=False,
                    result=None,
                    error=f"不支持的时间单位: {unit}"
                )
            
            # 执行操作
            if operation == "add":
                result_time = now + delta
                result = {
                    "当前时间": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "计算后时间": result_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "操作": f"增加 {amount} {unit}"
                }
            elif operation == "subtract":
                result_time = now - delta
                result = {
                    "当前时间": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "计算后时间": result_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "操作": f"减去 {amount} {unit}"
                }
            elif operation == "diff":
                result = {
                    "时间间隔": f"{amount} {unit}",
                    "等于秒数": delta.total_seconds(),
                    "等于分钟": delta.total_seconds() / 60,
                    "等于小时": delta.total_seconds() / 3600,
                    "等于天数": delta.total_seconds() / 86400
                }
            else:
                return ToolOutput(
                    success=False,
                    result=None,
                    error=f"不支持的操作: {operation}"
                )
            
            return ToolOutput(
                success=True,
                result=result,
                metadata={"operation": operation, "unit": unit, "amount": amount}
            )
            
        except Exception as e:
            return ToolOutput(
                success=False,
                result=None,
                error=f"时间计算失败: {str(e)}"
            )


class UnitConverterTool(Tool):
    """单位转换工具 - 各种单位换算"""
    
    def _get_name(self) -> str:
        return "convert_unit"
    
    def _get_description(self) -> str:
        return "转换各种单位。支持长度、重量、温度等常见单位的转换。"
    
    def _get_category(self) -> ToolCategory:
        return ToolCategory.CALCULATION
    
    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "value": {
                    "type": "number",
                    "description": "要转换的数值"
                },
                "from_unit": {
                    "type": "string",
                    "description": "源单位，如：m, km, kg, lb, celsius, fahrenheit"
                },
                "to_unit": {
                    "type": "string",
                    "description": "目标单位"
                }
            },
            "required": ["value", "from_unit", "to_unit"]
        }
    
    async def _execute(self, value: float, from_unit: str, to_unit: str) -> ToolOutput:
        """转换单位"""
        try:
            # 定义转换规则（转换到基础单位）
            conversions = {
                # 长度（基础单位：米）
                "m": 1,
                "km": 1000,
                "cm": 0.01,
                "mm": 0.001,
                "mile": 1609.34,
                "yard": 0.9144,
                "foot": 0.3048,
                "inch": 0.0254,
                
                # 重量（基础单位：千克）
                "kg": 1,
                "g": 0.001,
                "mg": 0.000001,
                "ton": 1000,
                "lb": 0.453592,
                "oz": 0.0283495,
                
                # 温度需要特殊处理
            }
            
            # 特殊处理温度转换
            if from_unit.lower() in ["celsius", "fahrenheit", "kelvin"]:
                result_value = self._convert_temperature(value, from_unit, to_unit)
                if result_value is None:
                    return ToolOutput(
                        success=False,
                        result=None,
                        error="温度单位转换失败"
                    )
            else:
                # 通用单位转换
                if from_unit not in conversions or to_unit not in conversions:
                    return ToolOutput(
                        success=False,
                        result=None,
                        error=f"不支持的单位: {from_unit} 或 {to_unit}"
                    )
                
                # 先转换到基础单位，再转换到目标单位
                base_value = value * conversions[from_unit]
                result_value = base_value / conversions[to_unit]
            
            result = {
                "原值": f"{value} {from_unit}",
                "转换后": f"{result_value:.4f} {to_unit}",
                "精确值": result_value
            }
            
            return ToolOutput(
                success=True,
                result=result,
                metadata={"from": from_unit, "to": to_unit}
            )
            
        except Exception as e:
            return ToolOutput(
                success=False,
                result=None,
                error=f"单位转换失败: {str(e)}"
            )
    
    def _convert_temperature(self, value: float, from_unit: str, to_unit: str) -> float:
        """温度转换"""
        from_unit = from_unit.lower()
        to_unit = to_unit.lower()
        
        # 先转换到摄氏度
        if from_unit == "celsius":
            celsius = value
        elif from_unit == "fahrenheit":
            celsius = (value - 32) * 5/9
        elif from_unit == "kelvin":
            celsius = value - 273.15
        else:
            return None
        
        # 从摄氏度转换到目标单位
        if to_unit == "celsius":
            return celsius
        elif to_unit == "fahrenheit":
            return celsius * 9/5 + 32
        elif to_unit == "kelvin":
            return celsius + 273.15
        else:
            return None