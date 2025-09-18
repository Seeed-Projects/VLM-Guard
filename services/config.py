#!/usr/bin/env python3
"""
配置管理模块

该模块负责管理应用程序的配置
"""

from typing import Union


class AppConfig:
    """应用程序配置类"""
    
    def __init__(self):
        # 网络配置
        self.port: int = 5000
        self.host: str = "localhost"
        
        # 视频流配置
        self.description_interval: int = 5
        self.model_name: str = "gemma3:4b"
        self.video_source: Union[int, str] = 0
        
        # vLLM配置
        self.vllm_url: str = "http://localhost:11434/v1/completions"
        
        # RS485配置
        self.enable_rs485_direct: bool = False
        self.rs485_port: str = "/dev/ttyTHS1"
        self.rs485_baud: int = 9600
        self.lux_sensor_addr: int = 0x0B
        self.light_control_addr: int = 0x01


class RS485Config:
    """RS485设备配置类"""
    
    def __init__(self):
        self.serial_port: str = "/dev/ttyTHS1"
        self.baud: int = 9600
        self.light_control_addr: int = 0x01
        self.light_sensor_addr: int = 0x0B