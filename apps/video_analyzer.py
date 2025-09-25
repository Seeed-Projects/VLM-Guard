#!/usr/bin/env python3
"""
VLM Demo 应用主入口

该应用整合了视频流传输、图像分析、MQTT数据处理和与vLLM对话的功能
"""

import argparse
import logging
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 现在可以正确导入services模块中的类
from services.config import AppConfig
from services.app_service import AppService

# 导入日志工具
from utils.logger import setup_logger

# 设置日志
logger = setup_logger("VLMApp")


def main():
    """主函数，程序入口点"""
    parser = argparse.ArgumentParser(
        description="VLM Demo 应用 - 危险行为检测",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                           # 使用默认参数启动（默认摄像头）
  %(prog)s --video-source 1          # 使用第二个摄像头
  %(prog)s --video-source video.mp4  # 使用视频文件
  %(prog)s --port 5001               # 使用5001端口
  %(prog)s --host 192.168.1.100      # 发送到指定主机
  %(prog)s --description-interval 10 # 每10秒生成一次分析
  %(prog)s --model llava:13b         # 使用llava:13b模型
  %(prog)s --vllm-url http://localhost:11434/v1/completions  # 使用指定的vLLM URL
        """
    )
    
    parser.add_argument(
        "--port", 
        type=int, 
        default=5000, 
        help="UDP端口号 (默认: 5000)"
    )
    parser.add_argument(
        "--host", 
        type=str, 
        default="localhost", 
        help="目标主机地址 (默认: localhost)"
    )
    parser.add_argument(
        "--description-interval", 
        type=int, 
        default=10, 
        help="危险行为分析间隔(秒) (默认: 10)"
    )
    parser.add_argument(
        "--model", 
        type=str, 
        default="gemma3:4b", 
        help="Ollama模型名称 (默认: gemma3:4b)"
    )
    parser.add_argument(
        "--video-source", 
        type=str, 
        default="0", 
        help="视频源: 0表示默认摄像头，其他数字表示摄像头索引，字符串表示视频文件路径 (默认: 0)"
    )
    parser.add_argument(
        "--vllm-url", 
        type=str, 
        default="http://localhost:11434/v1/completions", 
        help="vLLM API的URL (默认: http://localhost:11434/v1/completions)"
    )
    parser.add_argument(
        "--enable-rs485", 
        action="store_true", 
        help="启用RS485设备控制"
    )
    parser.add_argument(
        "--rs485-port", 
        type=str, 
        default="/dev/ttyTHS1", 
        help="RS485串口设备 (默认: /dev/ttyTHS1)"
    )
    parser.add_argument(
        "--rs485-baud", 
        type=int, 
        default=9600, 
        help="RS485波特率 (默认: 9600)"
    )
    parser.add_argument(
        "--lux-sensor-addr", 
        type=lambda x: int(x, 0), 
        default=0x0B, 
        help="光照传感器地址 (默认: 0x0B)"
    )
    parser.add_argument(
        "--light-control-addr", 
        type=lambda x: int(x, 0), 
        default=0x01, 
        help="灯光控制设备地址 (默认: 0x01)"
    )
    parser.add_argument(
        "--lux-topic", 
        type=str, 
        default="vlm/rs485/lux", 
        help="光照度数据MQTT主题 (默认: vlm/rs485/lux)"
    )
    parser.add_argument(
        "--light-control-topic", 
        type=str, 
        default="vlm/rs485/light/control", 
        help="灯光控制命令MQTT主题 (默认: vlm/rs485/light/control)"
    )
    parser.add_argument(
        "--light-status-topic", 
        type=str, 
        default="vlm/rs485/light/status", 
        help="灯光状态MQTT主题 (默认: vlm/rs485/light/status)"
    )
    parser.add_argument(
        "--enable-rs485-direct", 
        action="store_true", 
        help="启用直接RS485设备控制（不使用MQTT）"
    )
    
    args = parser.parse_args()
    
    # 创建应用配置
    config = AppConfig()
    config.port = args.port
    config.host = args.host
    config.description_interval = args.description_interval
    config.model_name = args.model
    config.video_source = args.video_source
    config.vllm_url = args.vllm_url
    config.enable_rs485_direct = args.enable_rs485_direct
    config.rs485_port = args.rs485_port
    config.rs485_baud = args.rs485_baud
    config.lux_sensor_addr = args.lux_sensor_addr
    config.light_control_addr = args.light_control_addr
    
    # 创建应用服务
    app_service = AppService(config)
    
    try:
        # 初始化组件
        app_service.initialize_rs485_components()
        app_service.initialize_video_streamer()
        
        # 启动RS485数据发送器
        app_service.start_rs485_data_sender()
        
        # 启动视频流传输
        app_service.start_video_streaming()
        
    except KeyboardInterrupt:
        logger.info("用户中断了应用")
    finally:
        # 停止所有组件
        app_service.stop_all_components()


if __name__ == "__main__":
    main()