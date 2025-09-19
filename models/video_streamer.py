#!/usr/bin/env python3
"""
视频流传输器模块 - 危险行为检测版

该模块实现了以下功能：
1. 从摄像头或视频文件捕获视频流
2. 通过UDP协议将视频帧发送到指定地址和端口
3. 定期将视频帧发送到LLaVA模型判断人的动作是否危险
4. 通过同一UDP端口将视频帧和判断结果发送到接收端
"""

import cv2
import socket
import threading
import time
import base64
import json
import os
import re
from datetime import datetime
import logging
import ollama
import requests
from typing import Optional, Any

from .rs485_sensor_data_sender import RS485SensorDataSender

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("VideoStreamer")


class VideoStreamer:
    """视频流传输器类
    
    该类负责：
    1. 从摄像头或视频文件捕获视频帧
    2. 通过UDP发送视频帧
    3. 定期将视频帧发送到LLaVA模型判断人的动作是否危险
    4. 通过UDP发送判断结果
    """
    
    def __init__(self, port: int = 5000, host: str = 'localhost', description_interval: int = 5, 
                 model_name: str = "gemma3:4b", video_source: Any = 0, 
                 vllm_url: str = "http://localhost:11434/v1/completions", 
                 rs485_sensor_data_sender: Optional[RS485SensorDataSender] = None):
        """
        初始化视频流传输器
        
        Args:
            port (int): 视频传输的UDP端口，默认为5000
            host (str): 主机地址，默认为'localhost'
            description_interval (int): 图像分析的时间间隔（秒），默认为5秒
            model_name (str): Ollama模型名称，默认为"gemma3:4b"
            video_source (int or str): 视频源，0表示默认摄像头，其他数字表示摄像头索引，字符串表示视频文件路径
            vllm_url (str): vLLM API的URL，默认为"http://localhost:11434/v1/completions"
            rs485_sensor_data_sender (RS485SensorDataSender): RS485传感器数据发送器实例
        """
        # 网络配置参数
        self.port = 5000  # 固定发送到5000端口
        self.host = host
        self.description_interval = description_interval
        
        # 网络通信相关属性
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.running = False
        
        # 视频捕获相关属性
        self.cap = None
        self.video_source = video_source
        self.last_description_time = 0
        self.frame_delay = 0.033  # 默认30fps的延迟
        
        # 图像分析相关属性
        self.latest_description = None
        self.description_lock = threading.Lock()
        self.analyzing = False
        self.analyzing_lock = threading.Lock()
        
        # 模型配置
        self.model_name = model_name
        self.vllm_url = vllm_url
        
        # RS485传感器数据发送器
        self.rs485_sensor_data_sender = rs485_sensor_data_sender
        
        logger.info(f"初始化视频流传输器，目标地址: {host}:{self.port}")
        logger.info(f"使用模型: {model_name}, 分析间隔: {description_interval}秒")
        logger.info(f"视频源: {video_source}")
        logger.info(f"vLLM URL: {vllm_url}")
    
    def __del__(self):
        """析构函数，确保socket被关闭"""
        if hasattr(self, 'socket'):
            self.socket.close()
    
    def send_frame_via_udp(self, frame, frame_type="video"):
        """
        通过UDP发送视频帧或分析结果
        
        Args:
            frame: OpenCV图像帧或分析结果字典
            frame_type (str): 帧类型，"video"表示视频帧，"description"表示分析结果，"vllm_response"表示vLLM响应
        """
        try:
            if frame_type == "video":
                # 处理视频帧数据
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 30])
                encoded_data = base64.b64encode(buffer).decode('utf-8')
                
                packet_data = {
                    "type": "video",
                    "data": encoded_data
                }
            else:  # description or vllm_response
                # 处理分析结果数据或vLLM响应
                packet_data = {
                    "type": frame_type,
                    "data": frame
                }
            
            # 发送数据包
            packet_json = json.dumps(packet_data)
            # 检查数据包大小
            packet_size = len(packet_json.encode('utf-8'))
            if packet_size > 65000:
                logger.warning(f"数据包大小 {packet_size} 字节，可能超出UDP限制")
            
            self.socket.sendto(packet_json.encode('utf-8'), (self.host, self.port))
        except Exception as e:
            logger.error(f"发送数据时出错: {e}")
    
    def encode_image_to_base64(self, image):
        """将OpenCV图像编码为base64字符串"""
        _, buffer = cv2.imencode('.jpg', image)
        return base64.b64encode(buffer).decode('utf-8')
    
    
    def analyze_human_action_with_llava(self, image):
        """
        使用Ollama LLaVA模型判断图片中人的动作是否危险
        
        Args:
            image: OpenCV图像
            
        Returns:
            dict: 包含判断结果的字典，格式为 {"date": "时间", "description": "描述", "danger": true/false}
        """
        try:
            # 将图像编码为base64字符串
            base64_image = self.encode_image_to_base64(image)
            current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 使用ollama库调用模型，仅要求描述图片内容
            prompt = "Please describe this image in detail. Focus on what people are doing, objects present, and the overall scene. Limit your description to 75 words."
            
            logger.info(f"向Ollama模型发送请求: {self.model_name}")
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {
                        'role': 'user',
                        'content': prompt,
                        'images': [base64_image]
                    }
                ],
                options={
                    "temperature": 0  # 降低随机性以获得更一致的结果
                }
            )
            
            # 获取模型的描述
            description = response['message']['content']
            logger.info(f"原始响应: {description}")
            
            # 限制描述在75个单词内
            words = description.split()
            if len(words) > 75:
                description = ' '.join(words[:75])
            
            # 使用正则表达式判断是否危险
            # 定义危险关键词模式
            danger_patterns = [
                r'\b(knife|刀)\b',
                r'\b(gun|fists|firearm|fist|guns|枪|武器)\b',
                r'\b(fight|fighting|打架|violence|暴力)\b',
                r'\b(fire|火焰|smoke|烟雾)\b',
                r'\b(danger|危险)\b',
                r'\b(blood|血)\b',
                r'\b(weapon|武器)\b',
                r'\b(explosion|爆炸)\b',
                r'\b(accident|事故)\b'
            ]
            
            # 检查描述中是否包含危险关键词
            is_dangerous = False
            for pattern in danger_patterns:
                if re.search(pattern, description, re.IGNORECASE):
                    is_dangerous = True
                    break
            
            # 构造返回的JSON
            response_json = {
                "date": current_date,
                "description": description,
                "danger": is_dangerous
            }
            
            # 将response_json以Markdown格式写入data.md文件
            self.write_response_to_markdown(response_json)
            
            return response_json

        except Exception as e:
            logger.error(f"分析图像时出错: {e}")
            return None
    
    def write_response_to_markdown(self, response_json):
        """
        将response_json以Markdown格式写入data.md文件
        
        Args:
            response_json (dict): 包含分析结果的字典
        """
        try:
            # 创建Markdown格式的内容
            markdown_content = f"""
            **time**: {response_json.get('date', 'N/A')}
            **danger**: {'yes' if response_json.get('danger', False) else 'no'}
            **description**: {response_json.get('description', 'N/A')}
            """
            
            # 写入文件，使用追加模式
            with open('./data/data.md', 'a', encoding='utf-8') as f:
                f.write(markdown_content)
                
            logger.info("分析结果已写入data.md文件")
        except Exception as e:
            logger.error(f"写入Markdown文件时出错: {e}")
    
    def chat_with_vllm(self, prompt):
        """
        与vLLM进行对话，基于历史数据回答问题
        
        Args:
            prompt (str): 用户的问题
            
        Returns:
            str: vLLM的响应
        """
        try:
            # 读取data/data.md文件作为历史数据上下文
            context = ""
            context_file = './data/data.md'
            if os.path.exists(context_file):
                with open(context_file, 'r', encoding='utf-8') as f:
                    context = f.read()
            
            # 如果没有历史数据，提供一个默认的提示
            if not context:
                context = "No previous analysis data available."
            
            # 构造一个详细的提示，指导vLLM如何使用历史数据回答问题
            full_prompt = f"""You are an intelligent security monitoring assistant. Please provide an answer based on the following historical data and the user's question.

                            Historical Data:
                            {context}

                            User Question:
                            {prompt}

                            Please provide an accurate and helpful answer based on the historical data. If the question cannot be answered with the provided data, please state so clearly."""

            # 准备发送给vLLM的数据
            data = {
                "model": "gemma3:4b",  # 使用正确的模型名称
                "prompt": full_prompt,
                "max_tokens": 800,  # 增加token数量以获得更详细的回答
                "temperature": 0
            }
            
            # 发送请求到vLLM
            logger.info(f"向vLLM发送请求，基于历史数据回答问题: {prompt}")
            response = requests.post(self.vllm_url, json=data, timeout=60)  # 增加超时时间
            
            if response.status_code == 200:
                response_data = response.json()
                answer = response_data.get("choices", [{}])[0].get("text", "").strip()
                logger.info(f"vLLM基于历史数据的响应: {answer}")
                return answer
            else:
                logger.error(f"vLLM请求失败: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"与vLLM对话时出错: {e}")
            return None
    
    def process_frame_for_description(self, frame):
        """
        处理单个视频帧，发送到LLaVA模型判断人的动作是否危险
        
        Args:
            frame: OpenCV图像帧
        """
        current_time = time.time()
        
        # 检查是否达到了分析间隔时间并且没有正在进行的分析
        if (current_time - self.last_description_time >= self.description_interval and 
            not self.analyzing):
            
            with self.analyzing_lock:
                self.analyzing = True
            
            # 创建新的线程来异步处理图像分析
            description_thread = threading.Thread(
                target=self._async_describe_frame, 
                args=(frame,),
                daemon=True
            )
            description_thread.start()
            self.last_description_time = current_time
    
    def _async_describe_frame(self, frame):
        """
        异步处理图像分析
        
        Args:
            frame: OpenCV图像帧
        """
        try:
            # 保存当前帧到文件，供Web UI访问
            try:
                cv2.imwrite('latest_analysis_frame.jpg', frame)
                logger.info("Saved latest analysis frame to file")
            except Exception as e:
                logger.error(f"Error saving analysis frame to file: {e}")
            
            # 调用LLaVA模型进行分析
            description = self.analyze_human_action_with_llava(frame)
            print(description)
            if description:
                # 更新最新的分析结果
                with self.description_lock:
                    self.latest_description = description
                
                # 控制RS485灯光：根据vLLM判断结果设置灯光颜色
                if self.rs485_sensor_data_sender:
                    is_dangerous = description.get("danger", False)
                    self.rs485_sensor_data_sender.handle_vllm_danger_result(is_dangerous)
                
                # 发送完整的分析结果到UI（包括描述、危险标志和时间戳）
                self.send_frame_via_udp(description, frame_type="vllm_response")
                
        finally:
            # 无论成功与否，都标记分析完成
            with self.analyzing_lock:
                self.analyzing = False
    
    def start_streaming(self):
        """开始视频流传输"""
        # 处理视频源参数，如果是数字字符串则转换为整数
        video_source = self.video_source
        if isinstance(video_source, str) and video_source.isdigit():
            video_source = int(video_source)
        
        # 打开视频源（摄像头或视频文件）
        self.cap = cv2.VideoCapture(video_source)
        
        if not self.cap.isOpened():
            logger.error(f"无法打开视频源: {video_source}")
            return False
        
        # 获取视频源信息
        if isinstance(video_source, int):
            logger.info(f"打开摄像头 {video_source}")
        else:
            logger.info(f"打开视频文件: {video_source}")
            # 对于视频文件，获取帧率以控制播放速度
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.frame_delay = 1.0 / fps if fps > 0 else 0.033  # 默认30fps
            logger.info(f"视频文件帧率: {fps}")
        
        self.running = True
        logger.info(f"开始视频流传输到 {self.host}:{self.port}")
        logger.info(f"危险行为分析将每 {self.description_interval} 秒执行一次")
        logger.info("按 Ctrl+C 停止传输")
        
        try:
            
            while self.running:
                ret, frame = self.cap.read()
                
                if not ret:
                    # 如果是视频文件，重新开始播放
                    if isinstance(self.video_source, str):
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    else:
                        logger.error("无法捕获帧")
                        break
                
                # 通过UDP发送视频帧
                self.send_frame_via_udp(frame, frame_type="video")
                
                # 每隔一定时间发送帧到LLaVA进行分析
                self.process_frame_for_description(frame)
                
                # 控制帧率
                if isinstance(self.video_source, str):
                    # 对于视频文件，按实际帧率播放
                    time.sleep(self.frame_delay)
                else:
                    # 对于摄像头，保持固定的帧率
                    time.sleep(0.033)
                        
        except KeyboardInterrupt:
            logger.info("用户中断了视频流传输")
        except Exception as e:
            logger.error(f"视频流传输过程中发生错误: {e}")
        finally:
            self.stop_streaming()
        
        return True
    
    def stop_streaming(self):
        """停止视频流传输"""
        self.running = False
        if self.cap:
            self.cap.release()
        logger.info("视频流传输已停止")