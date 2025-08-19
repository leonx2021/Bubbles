# -*- coding: utf-8 -*-

"""
事件系统
"""

from enum import Enum
from typing import Any, Dict, List, Callable, Optional
from dataclasses import dataclass, field
import asyncio
import logging
from datetime import datetime


class EventType(Enum):
    """事件类型"""
    # 消息事件
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_SENT = "message_sent"
    
    # AI事件
    AI_THINKING = "ai_thinking"
    AI_RESPONSE = "ai_response"
    
    # 命令事件
    COMMAND_MATCHED = "command_matched"
    COMMAND_EXECUTED = "command_executed"
    
    # 系统事件
    BOT_STARTED = "bot_started"
    BOT_STOPPED = "bot_stopped"
    ERROR_OCCURRED = "error_occurred"
    
    # 用户事件
    FRIEND_ADDED = "friend_added"
    GROUP_JOINED = "group_joined"
    GROUP_MEMBER_ADDED = "group_member_added"


@dataclass
class Event:
    """事件数据"""
    type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    source: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source
        }


class EventBus:
    """异步事件总线"""
    
    def __init__(self):
        self._listeners: Dict[EventType, List[Callable]] = {}
        self._async_listeners: Dict[EventType, List[Callable]] = {}
        self.logger = logging.getLogger(__name__)
    
    def subscribe(self, event_type: EventType, callback: Callable) -> None:
        """订阅事件"""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)
        self.logger.debug(f"订阅事件 {event_type.value}: {callback.__name__}")
    
    def subscribe_async(self, event_type: EventType, callback: Callable) -> None:
        """订阅异步事件"""
        if event_type not in self._async_listeners:
            self._async_listeners[event_type] = []
        self._async_listeners[event_type].append(callback)
        self.logger.debug(f"订阅异步事件 {event_type.value}: {callback.__name__}")
    
    def emit(self, event_type: EventType, data: Dict[str, Any] = None, source: str = None) -> None:
        """发布事件"""
        event = Event(type=event_type, data=data or {}, source=source)
        self._emit_sync(event)
        asyncio.create_task(self._emit_async(event))
    
    def _emit_sync(self, event: Event) -> None:
        """同步发布事件"""
        if event.type in self._listeners:
            for callback in self._listeners[event.type]:
                try:
                    callback(event)
                except Exception as e:
                    self.logger.error(f"事件处理器出错 {event.type.value}: {e}")
    
    async def _emit_async(self, event: Event) -> None:
        """异步发布事件"""
        if event.type in self._async_listeners:
            tasks = []
            for callback in self._async_listeners[event.type]:
                try:
                    task = callback(event)
                    if asyncio.iscoroutine(task):
                        tasks.append(task)
                except Exception as e:
                    self.logger.error(f"异步事件处理器出错 {event.type.value}: {e}")
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    def clear(self) -> None:
        """清空所有监听器"""
        self._listeners.clear()
        self._async_listeners.clear()