# -*- coding: utf-8 -*-

"""
全新的微信机器人系统
"""

from .wechat_bot import WeChatBot
from .config import BotConfig
from .plugin_manager import PluginManager

__all__ = ['WeChatBot', 'BotConfig', 'PluginManager']
__version__ = "2.0.0"