# -*- coding: utf-8 -*-

"""
全新的微信机器人主类
"""

import time
import logging
import signal
import sys
from queue import Empty
from threading import Thread
from typing import Dict, List, Optional
import xml.etree.ElementTree as ET
import re

from wcferry import Wcf, WxMsg

from .config import BotConfig
from .events import EventBus, EventType
from .message_processor import MessageProcessor
from .ai_manager import AIManager
from .plugin_manager import PluginManager


class WeChatBot:
    """全新的微信机器人"""
    
    def __init__(self, config_path: str = "config.yaml"):
        # 加载配置
        self.config = BotConfig.from_file(config_path)
        
        # 初始化日志
        self.logger = logging.getLogger(__name__)
        
        # 初始化微信客户端
        self.wcf = Wcf(debug=False)
        self.wxid = self.wcf.get_self_wxid()
        self.all_contacts = self._get_all_contacts()
        
        # 消息发送频率控制
        self._msg_timestamps = []
        
        # 初始化事件总线
        self.event_bus = EventBus()
        
        # 初始化消息处理器
        self.message_processor = MessageProcessor(
            self.event_bus, 
            self.wxid, 
            self.all_contacts
        )
        
        # 初始化AI管理器
        self.ai_manager = AIManager(self.config, self.event_bus)
        
        # 初始化插件管理器
        self.plugin_manager = PluginManager(self.config, self.event_bus)
        
        # 设置事件监听
        self._setup_event_listeners()
        
        # 运行状态
        self.running = False
        
        self.logger.info("微信机器人初始化完成")
    
    def _get_all_contacts(self) -> Dict[str, str]:
        """获取所有联系人"""
        try:
            contacts = self.wcf.query_sql("MicroMsg.db", "SELECT UserName, NickName FROM Contact;")
            return {contact["UserName"]: contact["NickName"] for contact in contacts}
        except Exception as e:
            self.logger.error(f"获取联系人失败: {e}")
            return {}
    
    def _setup_event_listeners(self):
        """设置事件监听"""
        # 监听AI响应事件
        self.event_bus.subscribe(EventType.AI_RESPONSE, self._handle_ai_response)
        
        # 监听消息发送事件  
        self.event_bus.subscribe(EventType.MESSAGE_SENT, self._handle_message_send)
        
        # 监听错误事件
        self.event_bus.subscribe(EventType.ERROR_OCCURRED, self._handle_error)
        
        # 监听系统事件
        self.event_bus.subscribe(EventType.BOT_STARTED, self._handle_bot_started)
        self.event_bus.subscribe(EventType.BOT_STOPPED, self._handle_bot_stopped)
    
    def start(self) -> None:
        """启动机器人"""
        if self.running:
            self.logger.warning("机器人已经在运行")
            return
        
        self.logger.info("正在启动微信机器人...")
        
        try:
            # 加载插件
            self.plugin_manager.load_plugins()
            
            # 启动消息接收
            self._start_message_receiving()
            
            # 设置信号处理
            self._setup_signal_handlers()
            
            self.running = True
            
            # 发布启动事件
            self.event_bus.emit(EventType.BOT_STARTED, {"timestamp": time.time()})
            
            self.logger.info("微信机器人启动成功")
            
        except Exception as e:
            self.logger.error(f"启动机器人失败: {e}")
            raise
    
    def stop(self) -> None:
        """停止机器人"""
        if not self.running:
            return
        
        self.logger.info("正在停止微信机器人...")
        
        self.running = False
        
        try:
            # 发布停止事件
            self.event_bus.emit(EventType.BOT_STOPPED, {"timestamp": time.time()})
            
            # 清理插件
            self.plugin_manager.cleanup()
            
            # 清理AI管理器
            self.ai_manager.cleanup()
            
            # 清理微信客户端
            self.wcf.cleanup()
            
            # 清理事件总线
            self.event_bus.clear()
            
            self.logger.info("微信机器人已停止")
            
        except Exception as e:
            self.logger.error(f"停止机器人时出错: {e}")
    
    def _start_message_receiving(self) -> None:
        """启动消息接收"""
        def message_loop():
            self.wcf.enable_receiving_msg()
            
            while self.running and self.wcf.is_receiving_msg():
                try:
                    msg = self.wcf.get_msg()
                    self.logger.debug(f"收到消息: {msg}")
                    
                    # 处理特殊消息类型
                    if msg.type == 37:  # 好友请求
                        self._handle_friend_request(msg)
                    elif msg.type == 10000:  # 系统消息
                        self._handle_system_message(msg)
                    else:
                        # 使用消息处理器处理普通消息
                        result = self.message_processor.process_message(msg)
                        self.logger.debug(f"消息处理完成: {result['current_state']}")
                    
                except Empty:
                    continue
                except Exception as e:
                    self.logger.error(f"处理消息时出错: {e}")
                    self.event_bus.emit(
                        EventType.ERROR_OCCURRED,
                        {"error": str(e), "context": "message_receiving"}
                    )
        
        # 启动消息接收线程
        thread = Thread(target=message_loop, name="MessageReceiver", daemon=True)
        thread.start()
        
        self.logger.info("消息接收已启动")
    
    def _setup_signal_handlers(self) -> None:
        """设置信号处理"""
        def signal_handler(sig, frame):
            self.logger.info("收到停止信号")
            self.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _handle_ai_response(self, event) -> None:
        """处理AI响应事件"""
        data = event.data
        text = data.get('text', '')
        chat_id = data.get('chat_id', '')
        
        if text and chat_id:
            # 更新消息处理器状态
            # 这里可以通过消息处理器的状态更新机制来设置AI响应
            pass
    
    def _handle_message_send(self, event) -> None:
        """处理消息发送事件"""
        data = event.data
        text = data.get('text', '')
        chat_id = data.get('chat_id', '')
        
        if text and chat_id:
            self.send_text_message(text, chat_id)
    
    def _handle_error(self, event) -> None:
        """处理错误事件"""
        error = event.data.get('error', 'Unknown error')
        context = event.data.get('context', 'Unknown')
        
        self.logger.error(f"系统错误 [{context}]: {error}")
    
    def _handle_bot_started(self, event) -> None:
        """处理机器人启动事件"""
        self.logger.info("机器人启动事件已触发")
        
        # 可以在这里添加启动后的初始化逻辑
        # 比如发送启动通知给管理员等
        admin_users = self.config.admin_users
        if admin_users:
            startup_msg = f"🤖 {self.config.bot_name} 已启动"
            for admin_id in admin_users:
                self.send_text_message(startup_msg, admin_id)
    
    def _handle_bot_stopped(self, event) -> None:
        """处理机器人停止事件"""
        self.logger.info("机器人停止事件已触发")
    
    def _handle_friend_request(self, msg: WxMsg) -> None:
        """处理好友请求"""
        if not self.config.auto_accept_friends:
            return
        
        try:
            xml = ET.fromstring(msg.content)
            v3 = xml.attrib["encryptusername"]
            v4 = xml.attrib["ticket"]
            scene = int(xml.attrib["scene"])
            
            self.wcf.accept_new_friend(v3, v4, scene)
            self.logger.info("自动接受好友请求")
            
            # 发布好友添加事件
            self.event_bus.emit(EventType.FRIEND_ADDED, {
                "user_id": v3,
                "scene": scene
            })
            
        except Exception as e:
            self.logger.error(f"处理好友请求失败: {e}")
    
    def _handle_system_message(self, msg: WxMsg) -> None:
        """处理系统消息"""
        try:
            # 处理新成员入群
            if "加入了群聊" in msg.content and msg.from_group():
                match = re.search(r'"(.+?)"邀请"(.+?)"加入了群聊', msg.content)
                if match:
                    inviter = match.group(1)
                    new_member = match.group(2)
                    
                    # 发布群成员添加事件
                    self.event_bus.emit(EventType.GROUP_MEMBER_ADDED, {
                        "group_id": msg.roomid,
                        "new_member": new_member,
                        "inviter": inviter
                    })
                    
                    # 发送欢迎消息
                    welcome_msg = self.config.welcome_message.format(
                        name=new_member,
                        inviter=inviter
                    )
                    self.send_text_message(welcome_msg, msg.roomid)
                    
                    self.logger.info(f"新成员 {new_member} 加入群聊 {msg.roomid}")
            
            # 处理新好友添加确认
            elif "你已添加了" in msg.content:
                match = re.findall(r"你已添加了(.*)，现在可以开始聊天了。", msg.content)
                if match:
                    friend_name = match[0]
                    self.all_contacts[msg.sender] = friend_name
                    
                    # 发送打招呼消息
                    greeting = f"Hi {friend_name}，我是{self.config.bot_name}，很高兴认识你！"
                    self.send_text_message(greeting, msg.sender)
                    
                    self.logger.info(f"已向新好友 {friend_name} 发送打招呼消息")
        
        except Exception as e:
            self.logger.error(f"处理系统消息失败: {e}")
    
    def send_text_message(self, text: str, chat_id: str, at_users: List[str] = None) -> bool:
        """发送文本消息"""
        try:
            # 频率限制检查
            if not self._check_rate_limit():
                self.logger.warning("消息发送频率超限")
                return False
            
            # 处理@用户
            at_list = ""
            if at_users:
                if "notify@all" in at_users:
                    text = f" @所有人\n\n{text}"
                    at_list = "notify@all"
                else:
                    ats = []
                    for user_id in at_users:
                        user_name = self.wcf.get_alias_in_chatroom(user_id, chat_id)
                        ats.append(f"@{user_name}")
                    
                    if ats:
                        text = f"{' '.join(ats)}\n\n{text}"
                        at_list = ",".join(at_users)
            
            # 发送消息
            self.wcf.send_text(text, chat_id, at_list)
            
            self.logger.info(f"发送消息到 {chat_id}: {text[:50]}...")
            
            return True
            
        except Exception as e:
            self.logger.error(f"发送消息失败: {e}")
            return False
    
    def _check_rate_limit(self) -> bool:
        """检查消息发送频率限制"""
        if self.config.message_rate_limit <= 0:
            return True
        
        current_time = time.time()
        
        # 清理过期的时间戳
        self._msg_timestamps = [
            ts for ts in self._msg_timestamps
            if current_time - ts < 60
        ]
        
        # 检查是否超过限制
        if len(self._msg_timestamps) >= self.config.message_rate_limit:
            return False
        
        # 记录当前时间戳
        self._msg_timestamps.append(current_time)
        return True
    
    def run(self) -> None:
        """运行机器人（阻塞）"""
        self.start()
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("收到中断信号")
        finally:
            self.stop()
    
    # API方法
    def get_config(self) -> BotConfig:
        """获取配置"""
        return self.config
    
    def get_event_bus(self) -> EventBus:
        """获取事件总线"""
        return self.event_bus
    
    def get_plugin_manager(self) -> PluginManager:
        """获取插件管理器"""
        return self.plugin_manager
    
    def get_ai_manager(self) -> AIManager:
        """获取AI管理器"""
        return self.ai_manager
    
    def is_running(self) -> bool:
        """检查是否在运行"""
        return self.running
    
    def get_bot_info(self) -> Dict[str, any]:
        """获取机器人信息"""
        return {
            "name": self.config.bot_name,
            "wxid": self.wxid,
            "running": self.running,
            "plugins": self.plugin_manager.get_loaded_plugins(),
            "ai_models": self.ai_manager.get_available_models(),
            "contacts_count": len(self.all_contacts)
        }