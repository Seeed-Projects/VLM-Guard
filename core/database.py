#!/usr/bin/env python3
"""
数据库模型和初始化代码

该模块实现了SQLite数据库的初始化和ORM模型定义
"""

import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging

# 导入日志工具
from utils.logger import setup_logger

# 数据库文件路径
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'vlm_demo.db')
DB_URL = f'sqlite:///{DB_PATH}'

# 创建数据库引擎
engine = create_engine(DB_URL, echo=False)

# 创建基类
Base = declarative_base()

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 设置日志
logger = setup_logger("Database")

class AnalysisRecord(Base):
    """分析记录模型"""
    __tablename__ = "analysis_records"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.utcnow)
    description = Column(Text)
    danger = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<AnalysisRecord(id={self.id}, date={self.date}, danger={self.danger})>"

class ChatRecord(Base):
    """聊天记录模型"""
    __tablename__ = "chat_records"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_message = Column(Text)
    assistant_response = Column(Text)
    
    def __repr__(self):
        return f"<ChatRecord(id={self.id}, timestamp={self.timestamp})>"

def init_db():
    """初始化数据库"""
    # 创建数据目录（如果不存在）
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 初始化数据库
init_db()