#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
全新的微信机器人启动入口
"""

import sys
import os
import logging
from argparse import ArgumentParser
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from bot import WeChatBot

__version__ = "2.0.0"


def setup_logging(level: str = "INFO"):
    """设置日志"""
    # 创建日志目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 日志级别映射
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR
    }
    
    log_level = level_map.get(level.upper(), logging.INFO)
    
    # 配置日志格式
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # 设置根日志器
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.FileHandler(log_dir / "bot.log", encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # 设置第三方库日志级别
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def create_default_config():
    """创建默认配置文件"""
    config_content = """# 微信机器人配置文件

# 基础配置
bot_name: "智能助手"
admin_users:
  - "your_admin_wxid_here"

# AI模型配置
ai_models:
  chatgpt:
    enabled: true
    api_key: "your_openai_api_key"
    base_url: "https://api.openai.com/v1"
    model: "gpt-3.5-turbo"
    temperature: 0.7
    max_tokens: 2000
    timeout: 30
  
  deepseek:
    enabled: false
    api_key: "your_deepseek_api_key"
    base_url: "https://api.deepseek.com/v1"
    model: "deepseek-chat"
    temperature: 0.7
    max_tokens: 2000
    timeout: 30

default_ai_model: "chatgpt"

# 群组配置
groups:
  # "group_id_1":
  #   name: "测试群"
  #   enabled: true
  #   ai_model: "chatgpt"
  #   max_history: 50
  #   auto_reply: true

# 消息配置
message_rate_limit: 30  # 每分钟最多发送30条消息
auto_accept_friends: false
welcome_message: "欢迎 {name} 加入群聊！"

# 数据库配置
database_url: "sqlite:///data/bot.db"
max_history_days: 30

# 插件配置
plugins_enabled:
  - "weather_plugin"
  - "news_plugin"

plugin_configs: {}

# 定时任务配置
scheduled_tasks: {}
"""
    
    with open("config.yaml", "w", encoding="utf-8") as f:
        f.write(config_content)
    
    print("已创建默认配置文件 config.yaml")
    print("请编辑配置文件后重新启动")


def main():
    parser = ArgumentParser(description=f"微信机器人 v{__version__}")
    parser.add_argument('-c', '--config', default='config.yaml', help='配置文件路径')
    parser.add_argument('-l', '--log-level', default='INFO', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='日志级别')
    parser.add_argument('--create-config', action='store_true', help='创建默认配置文件')
    
    args = parser.parse_args()
    
    # 创建默认配置
    if args.create_config:
        create_default_config()
        return
    
    # 检查配置文件
    if not Path(args.config).exists():
        print(f"配置文件 {args.config} 不存在")
        print("使用 --create-config 创建默认配置文件")
        return
    
    # 设置日志
    setup_logging(args.log_level)
    
    logger = logging.getLogger(__name__)
    logger.info(f"微信机器人 v{__version__} 启动中...")
    
    try:
        # 创建并启动机器人
        bot = WeChatBot(args.config)
        
        logger.info("机器人启动成功，按 Ctrl+C 停止")
        
        # 运行机器人
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("用户中断，正在停止...")
    except Exception as e:
        logger.error(f"机器人运行出错: {e}", exc_info=True)
        sys.exit(1)
    
    logger.info("机器人已停止")


if __name__ == "__main__":
    main()