#!/usr/bin/env python3
"""
应用服务模块

该模块负责协调应用程序的各个组件
"""

import logging
import sys
import os
from typing import Optional

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 现在可以正确导入core模块中的类
from core.video_streamer import VideoStreamer
from core.rs485_controller import RS485Controller
from core.rs485_sensor_data_sender import RS485SensorDataSender
from services.config import AppConfig

# 导入日志工具
from utils.logger import setup_logger

# 设置日志
logger = setup_logger("AppService")


class AppService:
    """应用服务类"""
    
    def __init__(self, config: AppConfig):
        """
        初始化应用服务
        
        Args:
            config (AppConfig): 应用配置
        """
        self.config = config
        self.video_streamer: Optional[VideoStreamer] = None
        self.rs485_controller: Optional[RS485Controller] = None
        self.rs485_sensor_data_sender: Optional[RS485SensorDataSender] = None
        
    def initialize_rs485_components(self) -> None:
        """初始化RS485组件"""
        if self.config.enable_rs485_direct:
            # 创建RS485控制器实例
            self.rs485_controller = RS485Controller(
                serial_port=self.config.rs485_port,
                baud=self.config.rs485_baud,
                light_control_addr=self.config.light_control_addr,
                light_sensor_addr=self.config.lux_sensor_addr
            )
            
            # 创建RS485传感器数据发送器实例
            self.rs485_sensor_data_sender = RS485SensorDataSender(
                sensor_reader=self.rs485_controller,
                host=self.config.host,
                port=5000  # 使用5000端口发送传感器数据，与UnifiedReceiver监听的端口一致
            )
            
            logger.info("RS485组件已初始化")
    
    def initialize_video_streamer(self) -> None:
        """初始化视频流传输器"""
        self.video_streamer = VideoStreamer(
            port=self.config.port,
            host=self.config.host,
            description_interval=self.config.description_interval,
            model_name=self.config.model_name,
            video_source=self.config.video_source,
            vllm_url=self.config.vllm_url,
            rs485_sensor_data_sender=self.rs485_sensor_data_sender
        )
        
        logger.info("视频流传输器已初始化")
    
    def start_rs485_data_sender(self) -> None:
        """启动RS485数据发送器"""
        if self.rs485_sensor_data_sender:
            self.rs485_sensor_data_sender.start()
            logger.info("RS485传感器数据发送器已启动")
    
    def start_video_streaming(self) -> None:
        """启动视频流传输"""
        if self.video_streamer:
            self.video_streamer.start_streaming()
    
    def stop_all_components(self) -> None:
        """停止所有组件"""
        if self.video_streamer:
            self.video_streamer.stop_streaming()
            
        if self.rs485_sensor_data_sender:
            self.rs485_sensor_data_sender.stop()
            
        logger.info("所有组件已停止")