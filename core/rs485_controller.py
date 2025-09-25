#!/usr/bin/env python3
"""
RS485控制器模块

该模块实现了RS485灯光控制和传感器数据读取功能
"""

import json
import logging
import time
from datetime import datetime
from pymodbus.client import ModbusSerialClient as RTU

# 导入日志工具
from utils.logger import setup_logger

# 设置日志
logger = setup_logger("RS485Controller")


class RS485Controller:
    """RS485控制器类（集成灯光控制和传感器读取功能）"""
    
    def __init__(self, serial_port='/dev/ttyTHS1', baud=9600, light_control_addr=0x01, light_sensor_addr=0x0B):
        """
        初始化RS485控制器
        
        Args:
            serial_port (str): 串口设备路径
            baud (int): 波特率
            light_control_addr (int): 灯光控制设备地址
            light_sensor_addr (int): 光照传感器地址
        """
        # RS485配置
        self.serial_port = serial_port
        self.baud = baud
        self.light_control_addr = light_control_addr
        self.light_sensor_addr = light_sensor_addr
        
        # Modbus寄存器定义
        # 灯光控制寄存器
        self.REG_G, self.REG_Y, self.REG_R = 0x0000, 0x0001, 0x0002
        # 光照传感器寄存器
        self.REG_LUX_HIGH, self.REG_LUX_LOW = 0x0007, 0x0008
        
        # 初始化Modbus客户端
        self.client = RTU(port=self.serial_port, baudrate=self.baud,
                          bytesize=8, parity='N', stopbits=1, timeout=0.5)
        
        logger.info(f"初始化RS485控制器")
        logger.info(f"串口: {serial_port}:{baud}")
        logger.info(f"灯光控制地址: 0x{light_control_addr:02X}")
        logger.info(f"光照传感器地址: 0x{light_sensor_addr:02X}")
    
    def connect(self):
        """
        连接到RS485设备
        
        Returns:
            bool: 连接是否成功
        """
        try:
            if self.client.connect():
                logger.info("成功连接到RS485设备")
                return True
            else:
                logger.error("无法连接到RS485设备")
                return False
        except Exception as e:
            logger.error(f"连接RS485设备时出错: {e}")
            return False
    
    def disconnect(self):
        """断开RS485设备连接"""
        try:
            self.client.close()
            logger.info("已断开RS485设备连接")
        except Exception as e:
            logger.error(f"断开RS485设备连接时出错: {e}")
    
    def write_register(self, addr, reg, val):
        """
        写入Modbus寄存器
        
        Args:
            addr (int): 设备地址
            reg (int): 寄存器地址
            val (int): 写入值
            
        Returns:
            bool: 是否成功
        """
        try:
            result = self.client.write_register(reg, val, device_id=addr)
            return not result.isError()
        except Exception as e:
            logger.error(f"写入寄存器时出错: {e}")
            return False
    
    def set_light(self, color):
        """
        设置灯光颜色
        
        Args:
            color (str): 灯光命令 ("green", "yellow", "red", "danger", "dark", "off")
        """
        
        # 先关闭所有灯
        for r in (self.REG_G, self.REG_Y, self.REG_R):
            self.write_register(self.light_control_addr, r, 0)
        
        # 根据命令设置对应灯
        if color == "red":
            self.write_register(self.light_control_addr, self.REG_R, 1)
        elif color == "green":
            self.write_register(self.light_control_addr, self.REG_G, 1)
        elif color == "yellow":
            self.write_register(self.light_control_addr, self.REG_Y, 1)

        logger.info(f"灯光已设置为: {color}")
    
    def read_lux(self):
        """
        读取光照度值
        
        Returns:
            int: 光照度值，如果读取失败则返回None
        """
        try:
            time.sleep(0.02)
            # 在pymodbus 3.x中，使用device_id参数替代slave/unit参数
            rr = self.client.read_holding_registers(self.REG_LUX_HIGH, count=2, device_id=self.light_sensor_addr)
            time.sleep(0.02)
            if rr.isError():
                logger.error(f"读取光照度寄存器时出错: {rr}")
                return None
            
            # 检查寄存器值是否有效
            if not hasattr(rr, 'registers') or len(rr.registers) < 2:
                logger.error("读取到的寄存器数据不完整")
                return None
                
            hi, lo = rr.registers
            lux = (hi << 16) | lo 
            
            # 检查lux值是否在合理范围内
            if lux < 0 or lux > 100000:  # 假设合理范围是0-100000 Lux
                logger.warning(f"读取到异常的光照度值: {lux}")
                return None
                
            return lux
        except Exception as e:
            logger.error(f"读取光照度时发生异常: {e}")
            return None
    
    def lux_to_json(self, lux, err=None):
        """
        将光照度值转换为JSON格式
        
        Args:
            lux (int): 光照度值
            err (str): 错误信息
            
        Returns:
            str: JSON格式的字符串
        """
        data = {
            "timestamp": datetime.now().isoformat(),
            "lux": lux,
            "unit": "Lux"
        }
        if err:
            data["error"] = err
        return json.dumps(data)


def main():
    """主函数，用于测试RS485控制器（同时控制灯光和读取传感器数值）"""
    import argparse
    
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="RS485控制器测试工具")
    parser.add_argument(
        "--port",
        type=str,
        default="/dev/ttyTHS1",
        help="串口设备路径"
    )
    parser.add_argument(
        "--baud",
        type=int,
        default=9600,
        help="波特率"
    )
    parser.add_argument(
        "--light-addr",
        type=lambda x: int(x, 0),
        default=0x01,
        help="灯光控制地址 (默认: 0x01)"
    )
    parser.add_argument(
        "--sensor-addr",
        type=lambda x: int(x, 0),
        default=0x0B,
        help="光照传感器地址 (默认: 0x0B)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=30,
        help="测试持续时间(秒)"
    )
    
    args = parser.parse_args()
    
    # 创建RS485控制器实例
    controller = RS485Controller(
        serial_port=args.port,
        baud=args.baud,
        light_control_addr=args.light_addr,
        light_sensor_addr=args.sensor_addr
    )
    
    # 连接到RS485设备
    if not controller.connect():
        logger.error("无法连接到RS485设备")
        return
    
    # 灯光颜色列表
    colors = ["green", "yellow", "red"]
    color_index = 0
    
    logger.info("开始同时控制灯光和读取传感器数值测试...")
    logger.info(f"测试将持续 {args.duration} 秒")
    
    start_time = time.time()
    try:
        while (time.time() - start_time) < args.duration:
            # 每5秒切换一次灯光颜色
            if int(time.time() - start_time) % 5 == 0:
                controller.set_light(colors[color_index])
                color_index = (color_index + 1) % len(colors)
            
            # 读取光照度值
            lux = controller.read_lux()
            if lux is not None:
                json_data = controller.lux_to_json(lux)
                logger.info(f"光照度: {lux} Lux, JSON: {json_data}")
            else:
                json_data = controller.lux_to_json(None, "读取失败")
                logger.warning(f"读取光照度失败, JSON: {json_data}")
            
            # 等待1秒
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("用户中断测试")
    finally:
        # 关闭所有灯光
        controller.set_light("off")
        # 断开连接
        controller.disconnect()
        logger.info("测试结束")


if __name__ == "__main__":
    main()