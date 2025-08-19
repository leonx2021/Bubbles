# -*- coding: utf-8 -*-

"""
机器人配置管理
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
import yaml
import logging


@dataclass
class AIModelConfig:
    """AI模型配置"""
    name: str
    enabled: bool = True
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: int = 30
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GroupConfig:
    """群组配置"""
    id: str
    name: str = ""
    enabled: bool = True
    ai_model: str = "default"
    max_history: int = 50
    auto_reply: bool = True
    allowed_commands: List[str] = field(default_factory=list)


@dataclass
class BotConfig:
    """机器人配置"""
    # 基础配置
    bot_name: str = "智能助手"
    admin_users: List[str] = field(default_factory=list)
    
    # AI配置
    ai_models: Dict[str, AIModelConfig] = field(default_factory=dict)
    default_ai_model: str = "chatgpt"
    
    # 群组配置
    groups: Dict[str, GroupConfig] = field(default_factory=dict)
    
    # 消息配置
    message_rate_limit: int = 30  # 每分钟最多发送消息数
    auto_accept_friends: bool = False
    welcome_message: str = "欢迎 {name} 加入群聊！"
    
    # 数据库配置
    database_url: str = "sqlite:///data/bot.db"
    max_history_days: int = 30
    
    # 插件配置
    plugins_enabled: List[str] = field(default_factory=list)
    plugin_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # 定时任务配置
    scheduled_tasks: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    @classmethod
    def from_file(cls, config_path: str) -> 'BotConfig':
        """从文件加载配置"""
        path = Path(config_path)
        if not path.exists():
            logging.warning(f"配置文件 {config_path} 不存在，使用默认配置")
            return cls()
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            
            # 解析AI模型配置
            ai_models = {}
            for name, config in data.get('ai_models', {}).items():
                ai_models[name] = AIModelConfig(name=name, **config)
            
            # 解析群组配置
            groups = {}
            for group_id, config in data.get('groups', {}).items():
                groups[group_id] = GroupConfig(id=group_id, **config)
            
            return cls(
                bot_name=data.get('bot_name', cls.bot_name),
                admin_users=data.get('admin_users', []),
                ai_models=ai_models,
                default_ai_model=data.get('default_ai_model', cls.default_ai_model),
                groups=groups,
                message_rate_limit=data.get('message_rate_limit', cls.message_rate_limit),
                auto_accept_friends=data.get('auto_accept_friends', cls.auto_accept_friends),
                welcome_message=data.get('welcome_message', cls.welcome_message),
                database_url=data.get('database_url', cls.database_url),
                max_history_days=data.get('max_history_days', cls.max_history_days),
                plugins_enabled=data.get('plugins_enabled', []),
                plugin_configs=data.get('plugin_configs', {}),
                scheduled_tasks=data.get('scheduled_tasks', {}),
            )
            
        except Exception as e:
            logging.error(f"加载配置文件失败: {e}")
            return cls()
    
    def save_to_file(self, config_path: str) -> None:
        """保存配置到文件"""
        path = Path(config_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'bot_name': self.bot_name,
            'admin_users': self.admin_users,
            'ai_models': {
                name: {
                    'enabled': config.enabled,
                    'api_key': config.api_key,
                    'base_url': config.base_url,
                    'model': config.model,
                    'temperature': config.temperature,
                    'max_tokens': config.max_tokens,
                    'timeout': config.timeout,
                    'extra_params': config.extra_params
                }
                for name, config in self.ai_models.items()
            },
            'default_ai_model': self.default_ai_model,
            'groups': {
                group_id: {
                    'name': config.name,
                    'enabled': config.enabled,
                    'ai_model': config.ai_model,
                    'max_history': config.max_history,
                    'auto_reply': config.auto_reply,
                    'allowed_commands': config.allowed_commands
                }
                for group_id, config in self.groups.items()
            },
            'message_rate_limit': self.message_rate_limit,
            'auto_accept_friends': self.auto_accept_friends,
            'welcome_message': self.welcome_message,
            'database_url': self.database_url,
            'max_history_days': self.max_history_days,
            'plugins_enabled': self.plugins_enabled,
            'plugin_configs': self.plugin_configs,
            'scheduled_tasks': self.scheduled_tasks,
        }
        
        try:
            with open(path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            logging.info(f"配置已保存到 {config_path}")
        except Exception as e:
            logging.error(f"保存配置文件失败: {e}")
    
    def get_ai_model_config(self, model_name: str) -> Optional[AIModelConfig]:
        """获取AI模型配置"""
        return self.ai_models.get(model_name)
    
    def get_group_config(self, group_id: str) -> Optional[GroupConfig]:
        """获取群组配置"""
        return self.groups.get(group_id)
    
    def is_admin(self, user_id: str) -> bool:
        """检查是否为管理员"""
        return user_id in self.admin_users