#!/usr/bin/env python3
"""
数据可视化接收器模块

该模块实现了接收和处理可视化数据的功能
"""

import socket
import threading
import json
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DataVisualizerReceiver")


class DataVisualizerReceiver:
    """数据可视化接收器类"""
    
    def __init__(self, port=5002, host='localhost'):
        """
        初始化数据可视化接收器
        
        Args:
            port (int): 接收数据的UDP端口
            host (str): 主机地址
        """
        self.port = port
        self.host = host
        self.socket = None
        self.running = False
        self.latest_data = None
        self.data_lock = threading.Lock()
        
        logger.info(f"初始化数据可视化接收器，端口: {port}")
    
    def start_receiver(self):
        """启动数据接收器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind((self.host, self.port))
            self.running = True
            
            # 在单独的线程中接收数据
            receiver_thread = threading.Thread(target=self._receive_data, daemon=True)
            receiver_thread.start()
            
            logger.info(f"数据可视化接收器已在 {self.host}:{self.port} 启动")
        except Exception as e:
            logger.error(f"启动数据可视化接收器时出错: {e}")
    
    def _receive_data(self):
        """在后台线程中接收数据"""
        while self.running:
            try:
                # 接收数据
                data, addr = self.socket.recvfrom(65536)  # 缓冲区大小
                
                # 解析JSON数据
                packet = json.loads(data.decode('utf-8'))
                
                # 更新最新数据
                with self.data_lock:
                    self.latest_data = packet
                    
                logger.debug(f"接收到来自 {addr} 的数据: {packet}")
                
            except json.JSONDecodeError:
                logger.warning("接收到无效的JSON数据")
            except Exception as e:
                logger.error(f"接收数据时出错: {e}")
    
    def get_latest_data(self):
        """获取最新数据"""
        with self.data_lock:
            return self.latest_data.copy() if self.latest_data else None
    
    def stop_receiver(self):
        """停止数据接收器"""
        self.running = False
        if self.socket:
            self.socket.close()
        logger.info("数据可视化接收器已停止")