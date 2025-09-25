#!/usr/bin/env python3
"""
日志配置工具模块

该模块提供了统一的日志配置功能
"""

import logging
import os
from typing import Optional


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_format: Optional[str] = None,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    设置并返回一个配置好的日志记录器
    
    Args:
        name (str): 日志记录器名称
        level (int): 日志级别，默认为INFO
        log_format (str, optional): 日志格式，默认为标准格式
        log_file (str, optional): 日志文件路径，如果提供则同时输出到文件
        
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    # 如果没有提供格式，则使用默认格式
    if log_format is None:
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加处理器
    if not logger.handlers:
        # 创建格式化器
        formatter = logging.Formatter(log_format)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # 如果提供了日志文件路径，则创建文件处理器
        if log_file:
            # 确保日志目录存在
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
                
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    获取已存在的日志记录器或创建新的日志记录器
    
    Args:
        name (str): 日志记录器名称
        
    Returns:
        logging.Logger: 日志记录器
    """
    return logging.getLogger(name)