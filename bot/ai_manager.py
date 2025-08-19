# -*- coding: utf-8 -*-

"""
AI 管理器 - 统一管理所有AI模型
"""

from typing import Dict, Optional, List
import logging
from abc import ABC, abstractmethod

from .config import BotConfig, AIModelConfig
from .events import EventBus, EventType

# 导入AI提供者
from ai_providers.ai_chatgpt import ChatGPT
from ai_providers.ai_deepseek import DeepSeek  
from ai_providers.ai_gemini import Gemini
from ai_providers.ai_perplexity import Perplexity


class BaseAIProvider(ABC):
    """AI提供者基类"""
    
    def __init__(self, config: AIModelConfig):
        self.config = config
        self.name = config.name
        self.enabled = config.enabled
    
    @abstractmethod
    def generate_response(self, text: str, chat_id: str, context: Dict = None) -> str:
        """生成回复"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查是否可用"""
        pass


class ChatGPTProvider(BaseAIProvider):
    """ChatGPT提供者"""
    
    def __init__(self, config: AIModelConfig):
        super().__init__(config)
        if self.enabled:
            try:
                self.client = ChatGPT({
                    'api_key': config.api_key,
                    'base_url': config.base_url,
                    'model': config.model,
                    'temperature': config.temperature,
                    'max_tokens': config.max_tokens
                })
            except Exception as e:
                logging.error(f"初始化 ChatGPT 失败: {e}")
                self.enabled = False
    
    def generate_response(self, text: str, chat_id: str, context: Dict = None) -> str:
        if not self.enabled:
            raise RuntimeError("ChatGPT 未启用或初始化失败")
        
        try:
            return self.client.get_answer(text, wxid=chat_id)
        except Exception as e:
            logging.error(f"ChatGPT 响应失败: {e}")
            raise
    
    def is_available(self) -> bool:
        return self.enabled and hasattr(self, 'client')


class DeepSeekProvider(BaseAIProvider):
    """DeepSeek提供者"""
    
    def __init__(self, config: AIModelConfig):
        super().__init__(config)
        if self.enabled:
            try:
                self.client = DeepSeek({
                    'api_key': config.api_key,
                    'base_url': config.base_url,
                    'model': config.model,
                    'temperature': config.temperature,
                    'max_tokens': config.max_tokens
                })
            except Exception as e:
                logging.error(f"初始化 DeepSeek 失败: {e}")
                self.enabled = False
    
    def generate_response(self, text: str, chat_id: str, context: Dict = None) -> str:
        if not self.enabled:
            raise RuntimeError("DeepSeek 未启用或初始化失败")
        
        try:
            return self.client.get_answer(text, wxid=chat_id)
        except Exception as e:
            logging.error(f"DeepSeek 响应失败: {e}")
            raise
    
    def is_available(self) -> bool:
        return self.enabled and hasattr(self, 'client')


class GeminiProvider(BaseAIProvider):
    """Gemini提供者"""
    
    def __init__(self, config: AIModelConfig):
        super().__init__(config)
        if self.enabled:
            try:
                self.client = Gemini({
                    'api_key': config.api_key,
                    'model': config.model,
                    'temperature': config.temperature
                })
            except Exception as e:
                logging.error(f"初始化 Gemini 失败: {e}")
                self.enabled = False
    
    def generate_response(self, text: str, chat_id: str, context: Dict = None) -> str:
        if not self.enabled:
            raise RuntimeError("Gemini 未启用或初始化失败")
        
        try:
            return self.client.get_answer(text, wxid=chat_id)
        except Exception as e:
            logging.error(f"Gemini 响应失败: {e}")
            raise
    
    def is_available(self) -> bool:
        return self.enabled and hasattr(self, 'client')


class PerplexityProvider(BaseAIProvider):
    """Perplexity提供者"""
    
    def __init__(self, config: AIModelConfig):
        super().__init__(config)
        if self.enabled:
            try:
                self.client = Perplexity({
                    'api_key': config.api_key,
                    'model': config.model
                })
            except Exception as e:
                logging.error(f"初始化 Perplexity 失败: {e}")
                self.enabled = False
    
    def generate_response(self, text: str, chat_id: str, context: Dict = None) -> str:
        if not self.enabled:
            raise RuntimeError("Perplexity 未启用或初始化失败")
        
        try:
            return self.client.get_answer(text, wxid=chat_id)
        except Exception as e:
            logging.error(f"Perplexity 响应失败: {e}")
            raise
    
    def is_available(self) -> bool:
        return self.enabled and hasattr(self, 'client')


class AIManager:
    """AI管理器"""
    
    def __init__(self, config: BotConfig, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self.logger = logging.getLogger(__name__)
        
        # AI提供者注册表
        self.provider_classes = {
            'chatgpt': ChatGPTProvider,
            'deepseek': DeepSeekProvider,
            'gemini': GeminiProvider,
            'perplexity': PerplexityProvider
        }
        
        # 初始化的提供者实例
        self.providers: Dict[str, BaseAIProvider] = {}
        
        # 设置事件监听
        self._setup_event_listeners()
        
        # 初始化AI提供者
        self._init_providers()
    
    def _setup_event_listeners(self):
        """设置事件监听"""
        self.event_bus.subscribe(EventType.AI_THINKING, self._handle_ai_thinking)
    
    def _init_providers(self):
        """初始化AI提供者"""
        for name, ai_config in self.config.ai_models.items():
            if name in self.provider_classes:
                try:
                    provider_class = self.provider_classes[name]
                    provider = provider_class(ai_config)
                    
                    if provider.is_available():
                        self.providers[name] = provider
                        self.logger.info(f"AI提供者 {name} 初始化成功")
                    else:
                        self.logger.warning(f"AI提供者 {name} 不可用")
                        
                except Exception as e:
                    self.logger.error(f"初始化AI提供者 {name} 失败: {e}")
            else:
                self.logger.warning(f"未知的AI提供者: {name}")
        
        if not self.providers:
            self.logger.error("没有可用的AI提供者")
        else:
            self.logger.info(f"成功初始化 {len(self.providers)} 个AI提供者")
    
    def _handle_ai_thinking(self, event):
        """处理AI思考事件"""
        data = event.data
        text = data.get('text', '')
        chat_id = data.get('chat_id', '')
        context = data.get('context', {})
        
        try:
            # 选择AI模型
            model_name = self._select_model(chat_id)
            
            if model_name not in self.providers:
                self.logger.error(f"AI模型 {model_name} 不可用")
                return
            
            # 生成回复
            provider = self.providers[model_name]
            response = provider.generate_response(text, chat_id, context)
            
            # 发布AI响应事件
            self.event_bus.emit(
                EventType.AI_RESPONSE,
                {
                    'text': response,
                    'chat_id': chat_id,
                    'model_used': model_name,
                    'original_text': text
                }
            )
            
            self.logger.info(f"AI响应生成完成: {model_name}")
            
        except Exception as e:
            self.logger.error(f"AI处理失败: {e}")
            self.event_bus.emit(
                EventType.ERROR_OCCURRED,
                {
                    'error': str(e),
                    'context': 'ai_processing',
                    'data': data
                }
            )
    
    def _select_model(self, chat_id: str) -> str:
        """选择AI模型"""
        # 检查群组配置
        group_config = self.config.get_group_config(chat_id)
        if group_config and group_config.ai_model in self.providers:
            return group_config.ai_model
        
        # 使用默认模型
        if self.config.default_ai_model in self.providers:
            return self.config.default_ai_model
        
        # 使用第一个可用模型
        if self.providers:
            return next(iter(self.providers.keys()))
        
        raise RuntimeError("没有可用的AI模型")
    
    def get_available_models(self) -> List[str]:
        """获取可用的AI模型列表"""
        return list(self.providers.keys())
    
    def is_model_available(self, model_name: str) -> bool:
        """检查指定模型是否可用"""
        return model_name in self.providers and self.providers[model_name].is_available()
    
    def cleanup(self):
        """清理资源"""
        for provider in self.providers.values():
            try:
                if hasattr(provider, 'cleanup'):
                    provider.cleanup()
            except Exception as e:
                self.logger.error(f"清理AI提供者失败: {e}")
        
        self.providers.clear()
        self.logger.info("AI管理器已清理")