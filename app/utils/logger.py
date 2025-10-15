"""
日志配置模块
"""
import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logger(name: str = "ai_chat_rag", log_level: str = "INFO") -> logging.Logger:
    """
    配置并返回日志记录器
    
    Args:
        name: 日志记录器名称
        log_level: 日志级别
        
    Returns:
        配置好的日志记录器
    """
    # 创建日志目录
    log_dir = Path("./logs")
    log_dir.mkdir(exist_ok=True)
    
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器 - 所有日志
    log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 文件处理器 - 错误日志
    error_log_file = log_dir / f"error_{datetime.now().strftime('%Y%m%d')}.log"
    error_handler = logging.FileHandler(error_log_file, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    return logger


# 创建全局日志记录器
logger = setup_logger()