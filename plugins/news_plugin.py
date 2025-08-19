# -*- coding: utf-8 -*-

"""
新闻插件
"""

from typing import Dict, Callable, Any, List

from bot.plugin_manager import CommandPlugin, ScheduledPlugin, PluginInfo
from bot.events import EventType
from function.func_news import News


class NewsPlugin(CommandPlugin, ScheduledPlugin):
    """新闻插件"""
    
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            name="news",
            version="1.0.0",
            description="新闻查询和推送插件",
            author="Bot"
        )
    
    def get_commands(self) -> Dict[str, Callable]:
        return {
            "新闻": self._handle_news_command,
            "news": self._handle_news_command
        }
    
    def get_scheduled_tasks(self) -> Dict[str, Dict[str, Any]]:
        return {
            "morning_news": {
                "schedule": "07:30",
                "handler": self._send_morning_news,
                "args": [],
                "kwargs": {}
            }
        }
    
    def _handle_news_command(self, event_data: Dict) -> None:
        """处理新闻查询命令"""
        chat_id = event_data.get('chat_id', '')
        text = event_data.get('text', '')
        
        try:
            news = News()
            is_today, news_content = news.get_important_news()
            
            if news_content:
                # 发布AI响应事件
                self.event_bus.emit(
                    EventType.AI_RESPONSE,
                    {
                        'text': news_content,
                        'chat_id': chat_id,
                        'model_used': 'news_plugin',
                        'original_text': text
                    }
                )
            else:
                error_msg = "暂时无法获取新闻信息，请稍后再试"
                self.event_bus.emit(
                    EventType.AI_RESPONSE,
                    {
                        'text': error_msg,
                        'chat_id': chat_id,
                        'model_used': 'news_plugin',
                        'original_text': text
                    }
                )
            
        except Exception as e:
            self.logger.error(f"查询新闻失败: {e}")
            
            error_msg = f"抱歉，新闻查询失败: {str(e)}"
            self.event_bus.emit(
                EventType.AI_RESPONSE,
                {
                    'text': error_msg,
                    'chat_id': chat_id,
                    'model_used': 'news_plugin',
                    'original_text': text
                }
            )
    
    def _send_morning_news(self) -> None:
        """发送早报新闻"""
        try:
            news = News()
            is_today, news_content = news.get_important_news()
            
            if is_today and news_content:
                # 获取配置中的新闻推送接收者
                receivers = getattr(self.config, 'NEWS', [])
                
                if receivers:
                    for receiver_id in receivers:
                        self.event_bus.emit(
                            EventType.MESSAGE_SENT,
                            {
                                'text': f"📰 早间新闻\n\n{news_content}",
                                'chat_id': receiver_id
                            }
                        )
                    
                    self.logger.info(f"早间新闻推送完成，共推送给 {len(receivers)} 个接收者")
                else:
                    self.logger.info("未配置新闻推送接收者")
            else:
                self.logger.warning("没有获取到今日新闻或内容为空")
                
        except Exception as e:
            self.logger.error(f"推送早间新闻失败: {e}")