# -*- coding: utf-8 -*-

"""
消息处理器 - 基于 LangGraph
"""

from typing import Dict, Any, Optional, TypedDict, List
from enum import Enum
import re
import logging

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from wcferry import WxMsg
from .events import EventBus, EventType


class ProcessState(Enum):
    """处理状态"""
    RECEIVED = "received"
    ANALYZED = "analyzed"
    ROUTED = "routed"
    PROCESSED = "processed"
    RESPONDED = "responded"
    COMPLETED = "completed"
    FAILED = "failed"


class MessageState(TypedDict):
    """消息状态"""
    # 原始数据
    original_msg: WxMsg
    
    # 解析后的数据
    text_content: str
    sender_id: str
    sender_name: str
    chat_id: str
    is_group: bool
    is_at_bot: bool
    
    # 处理状态
    current_state: ProcessState
    
    # 处理结果
    matched_command: Optional[str]
    ai_response: Optional[str]
    final_response: Optional[str]
    
    # 错误信息
    error: Optional[str]
    
    # 上下文信息
    context: Dict[str, Any]


class MessageProcessor:
    """消息处理器"""
    
    def __init__(self, event_bus: EventBus, bot_wxid: str, all_contacts: Dict[str, str]):
        self.event_bus = event_bus
        self.bot_wxid = bot_wxid
        self.all_contacts = all_contacts
        self.logger = logging.getLogger(__name__)
        
        # 初始化状态图
        self._init_state_graph()
    
    def _init_state_graph(self):
        """初始化状态图"""
        workflow = StateGraph(MessageState)
        
        # 添加节点
        workflow.add_node("analyze", self._analyze_message)
        workflow.add_node("route", self._route_message)
        workflow.add_node("process", self._process_message)
        workflow.add_node("respond", self._respond_message)
        workflow.add_node("handle_error", self._handle_error)
        
        # 设置流程
        workflow.add_edge(START, "analyze")
        
        # 条件路由
        workflow.add_conditional_edges(
            "analyze",
            self._should_continue,
            {
                "continue": "route",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "route",
            self._should_process,
            {
                "process": "process",
                "skip": "respond",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "process",
            self._should_respond,
            {
                "respond": "respond",
                "error": "handle_error"
            }
        )
        
        workflow.add_edge("respond", END)
        workflow.add_edge("handle_error", END)
        
        # 编译状态图
        memory = MemorySaver()
        self.graph = workflow.compile(checkpointer=memory)
    
    def process_message(self, msg: WxMsg) -> Dict[str, Any]:
        """处理消息主入口"""
        # 创建初始状态
        initial_state = MessageState(
            original_msg=msg,
            text_content="",
            sender_id=msg.sender,
            sender_name="",
            chat_id=msg.roomid if msg.from_group() else msg.sender,
            is_group=msg.from_group(),
            is_at_bot=False,
            current_state=ProcessState.RECEIVED,
            matched_command=None,
            ai_response=None,
            final_response=None,
            error=None,
            context={}
        )
        
        # 发布消息接收事件
        self.event_bus.emit(
            EventType.MESSAGE_RECEIVED,
            {"msg": msg, "state": initial_state}
        )
        
        # 运行状态图
        config = {"configurable": {"thread_id": f"msg_{msg.id}"}}
        
        try:
            final_state = self.graph.invoke(initial_state, config)
            return final_state
        except Exception as e:
            self.logger.error(f"消息处理失败: {e}")
            return {**initial_state, "error": str(e), "current_state": ProcessState.FAILED}
    
    def _analyze_message(self, state: MessageState) -> MessageState:
        """分析消息"""
        try:
            msg = state['original_msg']
            
            # 解析文本内容
            text_content = self._extract_text_content(msg)
            
            # 获取发送者信息
            sender_name = self.all_contacts.get(msg.sender, f"用户{msg.sender[-4:]}")
            
            # 检查是否@机器人
            is_at_bot = False
            if state['is_group']:
                is_at_bot = msg.is_at(self.bot_wxid)
                if is_at_bot:
                    # 移除@前缀
                    text_content = re.sub(r"^@.*?\s*", "", text_content).strip()
            
            # 更新状态
            state.update({
                'text_content': text_content,
                'sender_name': sender_name,
                'is_at_bot': is_at_bot,
                'current_state': ProcessState.ANALYZED,
                'context': {
                    'msg_type': msg.type,
                    'timestamp': msg.ts,
                    'is_self': msg.from_self()
                }
            })
            
            self.logger.debug(f"消息分析完成: {text_content[:50]}...")
            
        except Exception as e:
            state['error'] = str(e)
            state['current_state'] = ProcessState.FAILED
            self.logger.error(f"消息分析失败: {e}")
        
        return state
    
    def _route_message(self, state: MessageState) -> MessageState:
        """路由消息"""
        try:
            # 发布路由事件，让外部系统决定如何处理
            self.event_bus.emit(
                EventType.COMMAND_MATCHED,
                {
                    "text": state['text_content'],
                    "sender_id": state['sender_id'],
                    "chat_id": state['chat_id'],
                    "is_group": state['is_group'],
                    "is_at_bot": state['is_at_bot']
                }
            )
            
            state['current_state'] = ProcessState.ROUTED
            
        except Exception as e:
            state['error'] = str(e)
            state['current_state'] = ProcessState.FAILED
        
        return state
    
    def _process_message(self, state: MessageState) -> MessageState:
        """处理消息"""
        try:
            # 如果没有匹配到命令，且满足AI处理条件，则进行AI处理
            should_ai_process = (
                not state['matched_command'] and
                (not state['is_group'] or state['is_at_bot']) and
                state['text_content'].strip() != ""
            )
            
            if should_ai_process:
                # 发布AI思考事件
                self.event_bus.emit(
                    EventType.AI_THINKING,
                    {
                        "text": state['text_content'],
                        "sender_id": state['sender_id'],
                        "chat_id": state['chat_id'],
                        "context": state['context']
                    }
                )
            
            state['current_state'] = ProcessState.PROCESSED
            
        except Exception as e:
            state['error'] = str(e)
            state['current_state'] = ProcessState.FAILED
        
        return state
    
    def _respond_message(self, state: MessageState) -> MessageState:
        """响应消息"""
        try:
            # 确定最终响应内容
            final_response = state['ai_response'] or state['final_response']
            
            if final_response:
                # 发布消息发送事件
                self.event_bus.emit(
                    EventType.MESSAGE_SENT,
                    {
                        "text": final_response,
                        "chat_id": state['chat_id'],
                        "original_msg": state['original_msg']
                    }
                )
            
            state['current_state'] = ProcessState.COMPLETED
            
        except Exception as e:
            state['error'] = str(e)
            state['current_state'] = ProcessState.FAILED
        
        return state
    
    def _handle_error(self, state: MessageState) -> MessageState:
        """处理错误"""
        error = state.get('error', 'Unknown error')
        
        # 发布错误事件
        self.event_bus.emit(
            EventType.ERROR_OCCURRED,
            {
                "error": error,
                "state": state,
                "stage": state['current_state'].value
            }
        )
        
        self.logger.error(f"消息处理错误: {error}")
        return state
    
    def _extract_text_content(self, msg: WxMsg) -> str:
        """提取消息文本内容"""
        if msg.type == 1:  # 文本消息
            return msg.content.strip()
        elif msg.type == 49:  # 引用消息等
            # 简化处理，可以根据需要扩展
            return msg.content.strip()
        else:
            return ""
    
    # 条件判断方法
    def _should_continue(self, state: MessageState) -> str:
        return "error" if state['current_state'] == ProcessState.FAILED else "continue"
    
    def _should_process(self, state: MessageState) -> str:
        if state['current_state'] == ProcessState.FAILED:
            return "error"
        # 简化判断逻辑
        return "process"
    
    def _should_respond(self, state: MessageState) -> str:
        return "error" if state['current_state'] == ProcessState.FAILED else "respond"