#!/usr/bin/env python3
"""
VLM Demo Web UI

该模块实现了Web界面，用于显示视频流、分析结果和与vLLM交互
"""

import cv2
import socket
import threading
import time
import numpy as np
import base64
import json
import argparse
from datetime import datetime
from flask import Flask, render_template, Response, request, jsonify, send_file
import os
import logging

# 导入数据可视化接收器
from models.data_visualizer_receiver import DataVisualizerReceiver

# 导入数据库相关模块
from models.database import AnalysisRecord, ChatRecord, get_db

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("VLMWebUI")

class UnifiedReceiver:
    def __init__(self, port=5000, host='localhost', chart_port=5002):
        """
        初始化统一接收器（同时接收视频和描述）
        
        Args:
            port: 接收数据的UDP端口
            host: 主机地址
            chart_port: 接收图表数据的UDP端口
        """
        self.port = port
        self.host = host
        self.socket = None
        self.running = False
        self.frame = None
        self.frame_lock = threading.Lock()
        self.latest_description = None
        self.description_lock = threading.Lock()
        self.latest_analysis_frame = None
        self.analysis_frame_lock = threading.Lock()
        
        # 初始化数据可视化接收器
        self.chart_receiver = DataVisualizerReceiver(port=chart_port, host=host)
        self.latest_chart_data = None
        self.chart_data_lock = threading.Lock()
        
        # 光照度数据
        self.latest_lux_data = None
        self.lux_data_lock = threading.Lock()
        
    def start_receiver(self):
        """启动统一接收器"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.host, self.port))
        
        self.running = True
        logger.info(f"Starting unified receiver on {self.host}:{self.port}")
        
        # 在单独的线程中接收数据
        receiver_thread = threading.Thread(target=self._receive_data, daemon=True)
        receiver_thread.start()
        
        # 启动数据可视化接收器
        self.chart_receiver.start_receiver()
        
    def _receive_data(self):
        """在后台线程中接收视频帧和描述信息"""
        frame_count = 0
        desc_count = 0
        while self.running:
            try:
                # 接收数据
                data, addr = self.socket.recvfrom(65536)  # 缓冲区大小
                
                # 解析JSON数据
                packet = json.loads(data.decode('utf-8'))
                packet_type = packet.get("type")
                
                if packet_type == "video":
                    # 处理视频帧
                    base64_data = packet.get("data")
                    if base64_data:
                        # 将base64数据解码为图像
                        image_data = base64.b64decode(base64_data)
                        nparr = np.frombuffer(image_data, np.uint8)
                        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        
                        if frame is not None:
                            frame_count += 1
                            # 更新当前帧
                            with self.frame_lock:
                                self.frame = frame
                            
                            # 每30帧打印一次信息
                            if frame_count % 30 == 0:
                                logger.info(f"Received frame {frame_count} from {addr}: {frame.shape}")
                                
                elif packet_type == "description":
                    # 处理描述信息
                    data = packet.get("data")
                    if data is not None:
                        desc_count += 1
                        
                        # 检查数据格式（新格式包含帧和分析结果，旧格式只包含分析结果）
                        if isinstance(data, dict) and "analysis" in data:
                            # 新格式：包含帧和分析结果
                            description = data["analysis"]
                            frame_data = data["frame"]
                        else:
                            # 旧格式：只包含分析结果
                            description = data
                            frame_data = None
                        
                        # 对于新的JSON格式，我们直接使用返回的时间戳
                        # 如果没有时间戳，则使用当前时间
                        if isinstance(description, dict) and 'date' in description:
                            timestamp = description['date']
                        else:
                            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        
                        # 更新最新描述
                        with self.description_lock:
                            self.latest_description = {
                                'text': description,
                                'timestamp': timestamp
                            }
                        
                        # 更新分析帧（如果有）
                        if frame_data:
                            with self.analysis_frame_lock:
                                self.latest_analysis_frame = frame_data
                            # 保存帧到文件
                            self.save_latest_analysis_frame(frame_data)
                        
                        # 打印描述信息
                        if isinstance(description, dict):
                            logger.info(f"[ANALYSIS {desc_count} from {addr} at {timestamp}]")
                            logger.info(f"  Description: {description.get('description', 'N/A')}")
                            logger.info(f"  Danger: {description.get('danger', 'N/A')}")
                        else:
                            logger.info(f"[ANALYSIS {desc_count} from {addr} at {timestamp}] {description}")
                            
                elif packet_type == "vllm_response":
                    # 处理vLLM响应
                    vllm_response = packet.get("data")
                    logger.info(f"Received vllm_response: {vllm_response}")
                    if vllm_response is not None:
                        desc_count += 1
                        
                        # 直接使用vllm_response作为分析数据
                        analysis_data = vllm_response
                        frame_data = None  # 不从这个数据包中获取帧数据
                        
                        # 对于新的JSON格式，我们直接使用返回的时间戳
                        # 如果没有时间戳，则使用当前时间
                        if isinstance(analysis_data, dict) and 'date' in analysis_data:
                            timestamp = analysis_data['date']
                        else:
                            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        
                        # 更新最新描述
                        with self.description_lock:
                            self.latest_description = {
                                'text': analysis_data,
                                'timestamp': timestamp
                            }
                        logger.info(f"Updated latest_description: {self.latest_description}")
                        
                        # 打印vLLM响应信息
                        if isinstance(analysis_data, dict):
                            logger.info(f"[VLLM RESPONSE {desc_count} from {addr} at {timestamp}]")
                            logger.info(f"  Response: {analysis_data.get('description', 'N/A')}")
                            logger.info(f"  Danger: {analysis_data.get('danger', 'N/A')}")
                        else:
                            logger.info(f"[VLLM RESPONSE {desc_count} from {addr} at {timestamp}] {analysis_data}")
                            
                elif packet_type == "sensor_data":
                    # 处理传感器数据
                    sensor_data = packet.get("data")
                    if sensor_data is not None:
                        # 更新最新光照度数据
                        with self.lux_data_lock:
                            self.latest_lux_data = sensor_data
                        logger.info(f"[SENSOR DATA from {addr}] Lux: {sensor_data.get('lux', 'N/A')} {sensor_data.get('unit', '')}")
                        
            except json.JSONDecodeError:
                # 如果不是JSON格式，假设是旧格式的视频帧
                try:
                    nparr = np.frombuffer(data, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    if frame is not None:
                        frame_count += 1
                        # 更新当前帧
                        with self.frame_lock:
                            self.frame = frame
                        
                        # 每30帧打印一次信息
                        if frame_count % 30 == 0:
                            logger.info(f"Received frame {frame_count} from {addr}: {frame.shape}")
                except Exception as e:
                    logger.error(f"Error decoding old format frame: {e}")
            except Exception as e:
                logger.error(f"Error receiving data: {e}")
                
    def get_frame(self):
        """获取当前帧"""
        with self.frame_lock:
            return self.frame.copy() if self.frame is not None else None
            
    def get_latest_description(self):
        """获取最新描述"""
        with self.description_lock:
            return self.latest_description.copy() if self.latest_description else None
            
    def get_latest_analysis_frame(self):
        """获取最新的分析帧"""
        with self.analysis_frame_lock:
            return self.latest_analysis_frame
            
    def save_latest_analysis_frame(self, frame_data):
        """保存最新的分析帧到文件"""
        try:
            # 保存帧数据到文件
            with open('latest_analysis_frame.jpg', 'wb') as f:
                image_data = base64.b64decode(frame_data)
                f.write(image_data)
            logger.info("Saved latest analysis frame to file")
        except Exception as e:
            logger.error(f"Error saving analysis frame: {e}")
            
    def get_latest_chart_data(self):
        """获取最新的图表数据"""
        # 从数据可视化接收器获取最新数据
        chart_data = self.chart_receiver.get_latest_data()
        return chart_data
            
    def get_latest_lux_data(self):
        """获取最新的光照度数据"""
        with self.lux_data_lock:
            return self.latest_lux_data.copy() if self.latest_lux_data else None
            
    def stop_receiver(self):
        """停止统一接收器"""
        self.running = False
        if self.socket:
            self.socket.close()
        # 停止数据可视化接收器
        self.chart_receiver.stop_receiver()
        logger.info("Unified receiver stopped")


# Flask应用
app = Flask(__name__)
unified_receiver = None


def generate_frames():
    """生成视频帧用于网页流传输"""
    while True:
        if unified_receiver:
            frame = unified_receiver.get_frame()
            if frame is not None:
                try:
                    # 将帧编码为JPEG格式
                    ret, buffer = cv2.imencode('.jpg', frame)
                    if ret:
                        # 将帧作为字节流返回
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                except Exception as e:
                    logger.error(f"Error encoding frame: {e}")
        # 控制帧率
        time.sleep(0.033)  # 约30 FPS


@app.route('/')
def index():
    """主页路由"""
    return render_template('web_ui.html')


@app.route('/video_feed')
def video_feed():
    """视频流路由"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/latest_description')
def latest_description():
    """获取最新描述的路由"""
    if unified_receiver:
        description = unified_receiver.get_latest_description()
        return jsonify({'description': description})
    return jsonify({'description': None})





@app.route('/latest_analysis_frame')
def latest_analysis_frame():
    """获取最新分析帧的路由"""
    # 我们不再通过这个路由发送分析帧数据，因为帧数据会通过视频流单独发送
    return jsonify({'frame': None})


@app.route('/latest_chart_data')
def latest_chart_data():
    """获取最新图表数据的路由"""
    if unified_receiver:
        chart_data = unified_receiver.get_latest_chart_data()
        return jsonify({'chart_data': chart_data})
    return jsonify({'chart_data': None})


@app.route('/latest_lux_data')
def latest_lux_data():
    """获取最新光照度数据的路由"""
    if unified_receiver:
        lux_data = unified_receiver.get_latest_lux_data()
        return jsonify({'lux_data': lux_data})
    return jsonify({'lux_data': None})


@app.route('/analysis_frame_image')
def analysis_frame_image():
    """获取最新分析帧图像的路由"""
    try:
        if os.path.exists('latest_analysis_frame.jpg'):
            return send_file('latest_analysis_frame.jpg', mimetype='image/jpeg')
        else:
            # 返回一个默认的空白图像
            return Response('', mimetype='image/jpeg')
    except Exception as e:
        logger.error(f"Error serving analysis frame image: {e}")
        return Response('', mimetype='image/jpeg')


@app.route('/chat', methods=['POST'])
def chat():
    """与vLLM对话的路由"""
    try:
        # 检查Content-Type
        content_type = request.headers.get('Content-Type', '')
        logger.debug(f"Chat request Content-Type: {content_type}")
        
        # 尝试获取JSON数据
        try:
            data = request.json
            if data is None:
                logger.error("Failed to parse JSON data from request")
                return jsonify({'error': 'Invalid JSON data'}), 400
        except Exception as e:
            logger.error(f"Error parsing JSON data: {e}")
            return jsonify({'error': f'Error parsing JSON data: {e}'}), 400
            
        user_message = data.get('message', '')
        
        # 从数据库获取最近的20条分析记录作为上下文
        context = ""
        try:
            # 获取数据库会话
            db_gen = get_db()
            db = next(db_gen)
            
            # 查询最近的20条记录
            records = db.query(AnalysisRecord).order_by(AnalysisRecord.date.desc()).limit(20).all()
            
            # 构造上下文字符串
            for record in reversed(records):  # 按时间顺序排列
                context += f"""
                **time**: {record.date.strftime('%Y-%m-%d %H:%M:%S')}
                **danger**: {'yes' if record.danger else 'no'}
                **description**: {record.description}
                """
            
            # 关闭数据库会话
            try:
                next(db_gen)
            except StopIteration:
                pass
                
        except Exception as e:
            logger.error(f"从数据库获取历史记录时出错: {e}")
        
        # 如果没有历史数据，提供一个默认的提示
        if not context:
            context = "No previous analysis data available."
        
        # 构造一个详细的提示，指导vLLM如何使用历史数据回答问题
        full_prompt = f"""You are an intelligent security monitoring assistant. Please provide an answer based on the following historical data and the user's question.

Historical Data:
{context}

User Question:
{user_message}

Please provide an accurate and helpful answer based on the historical data. If the question cannot be answered with the provided data, please state so clearly."""

        # 准备发送给vLLM的数据
        vllm_data = {
            "model": "gemma3:4b",  # 根据实际模型名称调整
            "prompt": full_prompt,
            "stream": False,
            "max_tokens": 500,
            "temperature": 0
        }
        
        # 发送请求到vLLM
        import requests
        response = requests.post("http://localhost:11434/api/generate", json=vllm_data, timeout=30)
        
        if response.status_code == 200:
            response_data = response.json()
            response_text = response_data.get("response", "").strip()
        else:
            response_text = f"Error: vLLM request failed with status {response.status_code}"
        
        # 将对话记录保存到数据库
        try:
            # 获取数据库会话
            db_gen = get_db()
            db = next(db_gen)
            
            # 创建新的聊天记录
            chat_record = ChatRecord(
                user_message=user_message,
                assistant_response=response_text
            )
            
            # 添加到数据库
            db.add(chat_record)
            db.commit()
            db.refresh(chat_record)
            
            logger.info(f"聊天记录已保存到数据库，ID: {chat_record.id}")
            
            # 关闭数据库会话
            try:
                next(db_gen)
            except StopIteration:
                pass
                
        except Exception as e:
            logger.error(f"保存聊天记录到数据库时出错: {e}")
        
        return jsonify({
            'response': response_text,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({'error': str(e)}), 500


def start_web_ui(port=5000, host='localhost', web_port=5001, chart_port=5002):
    """启动Web UI服务器"""
    global unified_receiver
    
    # 初始化统一接收器
    unified_receiver = UnifiedReceiver(port=port, host=host, chart_port=chart_port)
    unified_receiver.start_receiver()
    
    logger.info(f"Starting web server on http://localhost:{web_port}")
    logger.info("Press Ctrl+C to stop")
    
    try:
        # 启动Flask应用
        app.run(host='0.0.0.0', port=web_port, debug=False, threaded=True)
    except KeyboardInterrupt:
        logger.info("\nStopping web server...")
    finally:
        unified_receiver.stop_receiver()


def main():
    """主函数"""
    # 设置命令行参数
    parser = argparse.ArgumentParser(description="VLM Demo Web UI")
    parser.add_argument("--port", type=int, default=5000, help="UDP port for receiving data (default: 5000)")
    parser.add_argument("--host", type=str, default="localhost", help="Host for UDP receiving (default: localhost)")
    parser.add_argument("--web-port", type=int, default=5001, help="Port for web server (default: 5001)")
    parser.add_argument("--chart-port", type=int, default=5002, help="Port for chart data receiving (default: 5002)")
    
    args = parser.parse_args()
    
    start_web_ui(port=args.port, host=args.host, web_port=args.web_port, chart_port=args.chart_port)


if __name__ == "__main__":
    main()