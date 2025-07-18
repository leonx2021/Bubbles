"""
AI路由功能注册
将需要通过AI路由的功能在这里注册
"""
import re
import json
import os
from typing import Optional, Match
from datetime import datetime

from .ai_router import ai_router
from .context import MessageContext

# ======== 天气功能 ========
@ai_router.register(
    name="weather_query",
    description="查询指定城市的天气情况和天气预报",
    examples=[
        "北京天气怎么样",
        "查一下上海的天气",
        "明天深圳会下雨吗",
        "杭州天气预报",
        "广州未来几天的天气"
    ],
    params_description="城市名称"
)
def ai_handle_weather(ctx: MessageContext, params: str) -> bool:
    """AI路由的天气查询处理"""
    city_name = params.strip()
    if not city_name:
        ctx.send_text("🤔 请告诉我你想查询哪个城市的天气")
        return True
    
    # 加载城市代码
    city_codes = {}
    city_code_path = os.path.join(os.path.dirname(__file__), '..', 'function', 'main_city.json')
    try:
        with open(city_code_path, 'r', encoding='utf-8') as f:
            city_codes = json.load(f)
    except Exception as e:
        if ctx.logger:
            ctx.logger.error(f"加载城市代码文件失败: {e}")
        ctx.send_text("⚠️ 抱歉，天气功能暂时不可用")
        return True
    
    # 查找城市代码
    city_code = city_codes.get(city_name)
    if not city_code:
        # 尝试模糊匹配
        for name, code in city_codes.items():
            if city_name in name:
                city_code = code
                city_name = name
                break
    
    if not city_code:
        ctx.send_text(f"😕 找不到城市 '{city_name}' 的天气信息")
        return True
    
    # 获取天气信息
    try:
        from function.func_weather import Weather
        weather_info = Weather(city_code).get_weather(include_forecast=True)
        ctx.send_text(weather_info)
        return True
    except Exception as e:
        if ctx.logger:
            ctx.logger.error(f"获取天气信息失败: {e}")
        ctx.send_text(f"😥 获取 {city_name} 天气时遇到问题")
        return True

# ======== 新闻功能 ========
@ai_router.register(
    name="news_query",
    description="获取当日新闻资讯",
    examples=[
        "看看今天的新闻",
        "有什么新闻吗",
        "最近发生了什么事",
        "今日要闻",
        "给我看看新闻"
    ],
    params_description="无需参数"
)
def ai_handle_news(ctx: MessageContext, params: str) -> bool:
    """AI路由的新闻查询处理"""
    try:
        from function.func_news import News
        news_instance = News()
        is_today, news_content = news_instance.get_important_news()
        
        if is_today:
            ctx.send_text(f"📰 今日要闻来啦：\n{news_content}")
        else:
            if news_content:
                ctx.send_text(f"ℹ️ 今日新闻暂未发布，为您找到最近的一条新闻：\n{news_content}")
            else:
                ctx.send_text("❌ 获取新闻失败，请稍后重试")
        
        return True
    except Exception as e:
        if ctx.logger:
            ctx.logger.error(f"获取新闻失败: {e}")
        ctx.send_text("❌ 获取新闻时发生错误")
        return True

# ======== 提醒功能 ========
@ai_router.register(
    name="reminder_set",
    description="设置提醒，支持一次性提醒、每日提醒、每周提醒",
    examples=[
        "提醒我明天下午3点开会",
        "每天早上8点提醒我吃早餐",
        "每周一提醒我周会",
        "下午5点提醒我下班",
        "设置一个提醒：周五下午检查周报"
    ],
    params_description="提醒的时间和内容描述"
)
def ai_handle_reminder_set(ctx: MessageContext, params: str) -> bool:
    """AI路由的提醒设置处理"""
    if not params.strip():
        at_list = ctx.msg.sender if ctx.is_group else ""
        ctx.send_text("请告诉我需要提醒什么内容和时间呀~", at_list)
        return True
    
    # 调用原有的提醒处理逻辑
    from .handlers import handle_reminder
    
    # 临时修改消息内容以适配原有处理器
    original_content = ctx.msg.content
    ctx.msg.content = f"提醒我{params}"
    
    # handle_reminder不使用match参数，直接传None
    result = handle_reminder(ctx, None)
    
    # 恢复原始内容
    ctx.msg.content = original_content
    
    return result

@ai_router.register(
    name="reminder_list",
    description="查看已设置的所有提醒",
    examples=[
        "查看我的提醒",
        "我有哪些提醒",
        "显示提醒列表",
        "我设置了什么提醒",
        "看看我的提醒"
    ],
    params_description="无需参数"
)
def ai_handle_reminder_list(ctx: MessageContext, params: str) -> bool:
    """AI路由的提醒列表查看处理"""
    from .handlers import handle_list_reminders
    return handle_list_reminders(ctx, None)

@ai_router.register(
    name="reminder_delete",
    description="删除已设置的提醒",
    examples=[
        "删除开会的提醒",
        "取消明天的提醒",
        "把早餐提醒删了",
        "删除所有提醒",
        "取消周会提醒"
    ],
    params_description="要删除的提醒描述或ID"
)
def ai_handle_reminder_delete(ctx: MessageContext, params: str) -> bool:
    """AI路由的提醒删除处理"""
    # 调用原有的删除提醒逻辑
    from .handlers import handle_delete_reminder
    
    # 临时修改消息内容
    original_content = ctx.msg.content
    ctx.msg.content = f"删除提醒 {params}"
    
    # handle_delete_reminder不使用match参数，直接传None
    result = handle_delete_reminder(ctx, None)
    
    # 恢复原始内容
    ctx.msg.content = original_content
    
    return result

# ======== Perplexity搜索功能 ========
@ai_router.register(
    name="perplexity_search",
    description="使用Perplexity AI进行深度研究，仅用于需要查询资料进行深度研究的场景",
    examples=[
        "搜索一下Python最新版本的特性",
        "帮我查查如何学习机器学习",
        "查找关于量子计算的最新进展",
        "搜索健康饮食的建议",
        "了解一下区块链技术"
    ],
    params_description="搜索查询内容"
)
def ai_handle_perplexity(ctx: MessageContext, params: str) -> bool:
    """AI路由的Perplexity搜索处理"""
    if not params.strip():
        at_list = ctx.msg.sender if ctx.is_group else ""
        ctx.send_text("请告诉我你想搜索什么内容", at_list)
        return True
    
    # 获取Perplexity实例
    perplexity_instance = getattr(ctx.robot, 'perplexity', None)
    if not perplexity_instance:
        ctx.send_text("❌ Perplexity搜索功能当前不可用")
        return True
    
    # 调用Perplexity处理
    content_for_perplexity = f"ask {params}"
    chat_id = ctx.get_receiver()
    sender_wxid = ctx.msg.sender
    room_id = ctx.msg.roomid if ctx.is_group else None
    is_group = ctx.is_group
    
    was_handled, fallback_prompt = perplexity_instance.process_message(
        content=content_for_perplexity,
        chat_id=chat_id,
        sender=sender_wxid,
        roomid=room_id,
        from_group=is_group,
        send_text_func=ctx.send_text
    )
    
    # 如果Perplexity无法处理，使用默认AI
    if not was_handled and fallback_prompt:
        chat_model = getattr(ctx, 'chat', None) or (getattr(ctx.robot, 'chat', None) if ctx.robot else None)
        if chat_model:
            try:
                import time
                current_time = time.strftime("%H:%M", time.localtime())
                q_with_info = f"[{current_time}] {ctx.sender_name}: {params}"
                
                rsp = chat_model.get_answer(
                    question=q_with_info,
                    wxid=ctx.get_receiver(),
                    system_prompt_override=fallback_prompt
                )
                
                if rsp:
                    at_list = ctx.msg.sender if ctx.is_group else ""
                    ctx.send_text(rsp, at_list)
                    return True
            except Exception as e:
                if ctx.logger:
                    ctx.logger.error(f"默认AI处理失败: {e}")
    
    return was_handled