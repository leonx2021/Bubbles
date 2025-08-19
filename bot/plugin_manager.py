# -*- coding: utf-8 -*-

"""
插件管理器
"""

import os
import sys
import importlib
import inspect
from typing import Dict, List, Any, Optional, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass
import logging

from .events import EventBus, EventType, Event
from .config import BotConfig


@dataclass
class PluginInfo:
    """插件信息"""
    name: str
    version: str
    description: str
    author: str
    enabled: bool = True
    dependencies: List[str] = None


class BasePlugin(ABC):
    """插件基类"""
    
    def __init__(self, config: BotConfig, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self.logger = logging.getLogger(f"Plugin.{self.name}")
    
    @property
    @abstractmethod
    def info(self) -> PluginInfo:
        """插件信息"""
        pass
    
    @property
    def name(self) -> str:
        """插件名称"""
        return self.info.name
    
    def on_load(self) -> None:
        """插件加载时调用"""
        pass
    
    def on_unload(self) -> None:
        """插件卸载时调用"""
        pass
    
    def on_enable(self) -> None:
        """插件启用时调用"""
        pass
    
    def on_disable(self) -> None:
        """插件禁用时调用"""
        pass


class CommandPlugin(BasePlugin):
    """命令插件基类"""
    
    @abstractmethod
    def get_commands(self) -> Dict[str, Callable]:
        """返回插件提供的命令
        
        返回格式: {"命令名": 处理函数}
        """
        pass


class EventPlugin(BasePlugin):
    """事件插件基类"""
    
    @abstractmethod
    def get_event_handlers(self) -> Dict[EventType, List[Callable]]:
        """返回插件的事件处理器
        
        返回格式: {EventType.MESSAGE_RECEIVED: [handler1, handler2]}
        """
        pass


class ScheduledPlugin(BasePlugin):
    """定时任务插件基类"""
    
    @abstractmethod
    def get_scheduled_tasks(self) -> Dict[str, Dict[str, Any]]:
        """返回插件的定时任务
        
        返回格式: {
            "task_name": {
                "schedule": "07:00",  # 每天07:00
                "handler": handler_function,
                "args": [],
                "kwargs": {}
            }
        }
        """
        pass


class PluginManager:
    """插件管理器"""
    
    def __init__(self, config: BotConfig, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self.logger = logging.getLogger(__name__)
        
        # 已加载的插件
        self.plugins: Dict[str, BasePlugin] = {}
        
        # 插件目录
        self.plugins_dir = "plugins"
        
        # 确保插件目录存在
        os.makedirs(self.plugins_dir, exist_ok=True)
        
        # 命令注册表
        self.commands: Dict[str, Callable] = {}
        
        # 定时任务注册表
        self.scheduled_tasks: Dict[str, Dict[str, Any]] = {}
    
    def load_plugins(self) -> None:
        """加载所有插件"""
        self.logger.info("开始加载插件...")
        
        # 将插件目录添加到 Python 路径
        if self.plugins_dir not in sys.path:
            sys.path.insert(0, self.plugins_dir)
        
        # 扫描插件目录
        for plugin_name in self.config.plugins_enabled:
            try:
                self._load_plugin(plugin_name)
            except Exception as e:
                self.logger.error(f"加载插件 {plugin_name} 失败: {e}")
        
        self.logger.info(f"插件加载完成，共加载 {len(self.plugins)} 个插件")
    
    def _load_plugin(self, plugin_name: str) -> None:
        """加载单个插件"""
        self.logger.debug(f"正在加载插件: {plugin_name}")
        
        try:
            # 动态导入插件模块
            module = importlib.import_module(plugin_name)
            
            # 查找插件类
            plugin_class = None
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, BasePlugin) and 
                    obj != BasePlugin):
                    plugin_class = obj
                    break
            
            if not plugin_class:
                raise ValueError(f"插件 {plugin_name} 中未找到插件类")
            
            # 实例化插件
            plugin_config = self.config.plugin_configs.get(plugin_name, {})
            plugin = plugin_class(self.config, self.event_bus)
            
            # 检查依赖
            if plugin.info.dependencies:
                for dep in plugin.info.dependencies:
                    if dep not in self.plugins:
                        raise ValueError(f"插件 {plugin_name} 依赖 {dep}，但 {dep} 未加载")
            
            # 调用插件的加载回调
            plugin.on_load()
            
            # 注册插件
            self.plugins[plugin_name] = plugin
            
            # 注册命令
            if isinstance(plugin, CommandPlugin):
                self._register_plugin_commands(plugin)
            
            # 注册事件处理器
            if isinstance(plugin, EventPlugin):
                self._register_plugin_events(plugin)
            
            # 注册定时任务
            if isinstance(plugin, ScheduledPlugin):
                self._register_plugin_tasks(plugin)
            
            # 启用插件
            if plugin.info.enabled:
                plugin.on_enable()
            
            self.logger.info(f"插件 {plugin_name} 加载成功")
            
        except Exception as e:
            self.logger.error(f"加载插件 {plugin_name} 失败: {e}")
            raise
    
    def _register_plugin_commands(self, plugin: CommandPlugin) -> None:
        """注册插件命令"""
        commands = plugin.get_commands()
        for cmd_name, handler in commands.items():
            if cmd_name in self.commands:
                self.logger.warning(f"命令 {cmd_name} 已存在，将被插件 {plugin.name} 覆盖")
            
            self.commands[cmd_name] = handler
            self.logger.debug(f"注册命令: {cmd_name} -> {plugin.name}")
    
    def _register_plugin_events(self, plugin: EventPlugin) -> None:
        """注册插件事件处理器"""
        event_handlers = plugin.get_event_handlers()
        for event_type, handlers in event_handlers.items():
            for handler in handlers:
                self.event_bus.subscribe(event_type, handler)
                self.logger.debug(f"注册事件处理器: {event_type.value} -> {plugin.name}")
    
    def _register_plugin_tasks(self, plugin: ScheduledPlugin) -> None:
        """注册插件定时任务"""
        tasks = plugin.get_scheduled_tasks()
        for task_name, task_config in tasks.items():
            full_task_name = f"{plugin.name}.{task_name}"
            self.scheduled_tasks[full_task_name] = task_config
            self.logger.debug(f"注册定时任务: {full_task_name}")
    
    def unload_plugin(self, plugin_name: str) -> None:
        """卸载插件"""
        if plugin_name not in self.plugins:
            self.logger.warning(f"插件 {plugin_name} 未加载")
            return
        
        try:
            plugin = self.plugins[plugin_name]
            
            # 禁用插件
            plugin.on_disable()
            
            # 卸载插件
            plugin.on_unload()
            
            # 移除命令
            if isinstance(plugin, CommandPlugin):
                commands = plugin.get_commands()
                for cmd_name in commands.keys():
                    self.commands.pop(cmd_name, None)
            
            # 移除定时任务
            if isinstance(plugin, ScheduledPlugin):
                tasks = plugin.get_scheduled_tasks()
                for task_name in tasks.keys():
                    full_task_name = f"{plugin.name}.{task_name}"
                    self.scheduled_tasks.pop(full_task_name, None)
            
            # 从插件列表中移除
            del self.plugins[plugin_name]
            
            self.logger.info(f"插件 {plugin_name} 卸载成功")
            
        except Exception as e:
            self.logger.error(f"卸载插件 {plugin_name} 失败: {e}")
    
    def reload_plugin(self, plugin_name: str) -> None:
        """重载插件"""
        self.unload_plugin(plugin_name)
        self._load_plugin(plugin_name)
    
    def get_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        """获取插件实例"""
        return self.plugins.get(plugin_name)
    
    def get_loaded_plugins(self) -> List[str]:
        """获取已加载的插件列表"""
        return list(self.plugins.keys())
    
    def get_plugin_info(self, plugin_name: str) -> Optional[PluginInfo]:
        """获取插件信息"""
        plugin = self.get_plugin(plugin_name)
        return plugin.info if plugin else None
    
    def get_all_commands(self) -> Dict[str, Callable]:
        """获取所有插件命令"""
        return self.commands.copy()
    
    def get_all_scheduled_tasks(self) -> Dict[str, Dict[str, Any]]:
        """获取所有定时任务"""
        return self.scheduled_tasks.copy()
    
    def execute_command(self, command_name: str, *args, **kwargs) -> Any:
        """执行命令"""
        if command_name not in self.commands:
            raise ValueError(f"未知命令: {command_name}")
        
        handler = self.commands[command_name]
        try:
            return handler(*args, **kwargs)
        except Exception as e:
            self.logger.error(f"执行命令 {command_name} 失败: {e}")
            raise
    
    def cleanup(self) -> None:
        """清理插件管理器"""
        self.logger.info("开始清理插件...")
        
        for plugin_name in list(self.plugins.keys()):
            try:
                self.unload_plugin(plugin_name)
            except Exception as e:
                self.logger.error(f"清理插件 {plugin_name} 失败: {e}")
        
        self.logger.info("插件管理器清理完成")