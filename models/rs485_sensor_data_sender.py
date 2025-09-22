#!/usr/bin/env python3
"""
RS485传感器数据发送器模块

该模块实现了RS485传感器数据的读取和发送功能
"""

import json
import logging
import socket
import threading
import time
from typing import Optional

from .rs485_controller import RS485Controller

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("RS485SensorDataSender")


class RS485SensorDataSender:
    """RS485传感器数据发送器类"""
    
    def __init__(self, sensor_reader: RS485Controller, host: str = 'localhost', port: int = 5000):
        """
        初始化RS485传感器数据发送器
        
        Args:
            sensor_reader (RS485Controller): RS485控制器实例
            host (str): 目标主机地址
            port (int): UDP端口
        """
        self.sensor_reader = sensor_reader
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        logger.info(f"初始化RS485传感器数据发送器，目标地址: {host}:{port}")
    
    def start(self) -> None:
        """启动数据发送器"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._send_data_loop, daemon=True)
            self.thread.start()
            logger.info("RS485传感器数据发送器已启动")
    
    def stop(self) -> None:
        """停止数据发送器"""
        if self.running:
            self.running = False
            if self.thread:
                self.thread.join(timeout=2)
            logger.info("RS485传感器数据发送器已停止")
    
    def handle_vllm_danger_result(self, is_dangerous: bool) -> None:
        """
        处理vLLM危险判断结果并控制灯光
        
        Args:
            is_dangerous (bool): 是否危险
        """
        try:
            if is_dangerous:
                # 当vLLM判断为危险时，将灯光设置为黄色
                self.sensor_reader.set_light("yellow")
                logger.info("vLLM判断为危险，灯光已设置为黄色")
            else:
                # 当vLLM判断为安全时，将灯光设置为绿色
                self.sensor_reader.set_light("green")
                logger.info("vLLM判断为安全，灯光已设置为绿色")
        except Exception as e:
            logger.error(f"设置灯光时出错: {e}")
    
    def _send_data_loop(self) -> None:
        """数据发送循环"""
        # 连接RS485设备
        if not self.sensor_reader.connect():
            logger.error("无法连接到RS485设备")
            self.running = False
            return
            
        while self.running:
            try:
                # 读取光照度数据
                lux = self.sensor_reader.read_lux()
                
                if lux is not None:
                    # 控制灯光颜色：当光照度小于50时设为红色，否则设为绿色
                    if lux < 50:
                        self.sensor_reader.set_light("red")
                    
                    # 创建数据包
                    data_packet = {
                        "type": "sensor_data",
                        "data": {
                            "lux": lux,
                            "unit": "Lux",
                            "timestamp": time.time()
                        }
                    }
                    
                    # 发送数据包
                    packet_json = json.dumps(data_packet)
                    self.socket.sendto(packet_json.encode('utf-8'), (self.host, self.port))
                    logger.debug(f"发送光照度数据: {lux} Lux")
                else:
                    logger.warning("无法读取光照度数据")
                
                # 每秒发送一次数据
                time.sleep(1)
            except Exception as e:
                logger.error(f"发送传感器数据时出错: {e}")
                time.sleep(1)
        
        # 断开RS485设备连接
        self.sensor_reader.disconnect()