# -*- coding: utf-8 -*-

"""
天气插件
"""

import re
from typing import Dict, Callable

from bot.plugin_manager import CommandPlugin, PluginInfo
from bot.events import EventType
from function.func_weather import Weather


class WeatherPlugin(CommandPlugin):
    """天气查询插件"""
    
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            name="weather",
            version="1.0.0",
            description="天气查询插件",
            author="Bot"
        )
    
    def get_commands(self) -> Dict[str, Callable]:
        return {
            "天气": self._handle_weather_command,
            "weather": self._handle_weather_command
        }
    
    def _handle_weather_command(self, event_data: Dict) -> None:
        """处理天气查询命令"""
        text = event_data.get('text', '')
        chat_id = event_data.get('chat_id', '')
        
        # 提取城市名称
        city_match = re.search(r'(天气|weather)\s*(.+)', text, re.IGNORECASE)
        if city_match:
            city_name = city_match.group(2).strip()
        else:
            city_name = "北京"  # 默认城市
        
        try:
            # 这里简化处理，实际应该根据城市名称获取城市代码
            weather = Weather("101010100")  # 北京的城市代码
            weather_info = weather.get_weather()
            
            # 发布AI响应事件
            self.event_bus.emit(
                EventType.AI_RESPONSE,
                {
                    'text': weather_info,
                    'chat_id': chat_id,
                    'model_used': 'weather_plugin',
                    'original_text': text
                }
            )
            
        except Exception as e:
            self.logger.error(f"查询天气失败: {e}")
            
            error_msg = f"抱歉，天气查询失败: {str(e)}"
            self.event_bus.emit(
                EventType.AI_RESPONSE,
                {
                    'text': error_msg,
                    'chat_id': chat_id,
                    'model_used': 'weather_plugin',
                    'original_text': text
                }
            )