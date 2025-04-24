# ai_providers/ai_gemini.py
#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import time
import httpx
import google.generativeai as genai
from google.api_core.exceptions import GoogleAPICallError, ClientError
from google.generativeai.types import BlockedPromptException, StopCandidateException

# 引入 MessageSummary 类型提示
try:
    from function.func_summary import MessageSummary
except ImportError:
    MessageSummary = object # Fallback

class Gemini:
    def __init__(self, conf: dict, message_summary_instance: MessageSummary = None, bot_wxid: str = None) -> None:
        self._api_key = conf.get("api_key")
        # 优先使用用户配置的模型，否则默认为 gemini-1.5-pro-latest (一个常用的强大模型)
        self._model_name = conf.get("model_name", "gemini-1.5-pro-latest")
        self._prompt = conf.get("prompt")
        self._proxy = conf.get("proxy")
        self.max_history_messages = conf.get("max_history_messages", 15) # Gemini 通常上下文窗口较大，可适当增加默认值
        self.LOG = logging.getLogger("Gemini")

        self.message_summary = message_summary_instance
        self.bot_wxid = bot_wxid
        if not self.message_summary:
             self.LOG.warning("MessageSummary 实例未提供给 Gemini，上下文功能将不可用！")
        if not self.bot_wxid:
             self.LOG.warning("bot_wxid 未提供给 Gemini，可能无法正确识别机器人自身消息！")

        try:
            # 配置代理 (如果提供)
            transport = None
            if self._proxy:
                # 支持 http 和 socks5 代理
                proxies = {
                    "http://": self._proxy,
                    "https://": self._proxy,
                }
                transport = httpx.HTTPTransport(proxy=proxies)
                self.LOG.info(f"Gemini 使用代理: {self._proxy}")

            genai.configure(api_key=self._api_key, transport=transport)
            # 初始化模型
            self._model = genai.GenerativeModel(
                self._model_name,
                # 默认系统提示，如果配置中未提供
                system_instruction=self._prompt if self._prompt else "You are a helpful assistant."
            )
            self.LOG.info(f"Gemini 模型 {self._model_name} 初始化成功")

            # 检查模型是否支持视觉 (简单检查，更可靠的方式是查询模型能力)
            # Gemini 1.5 Pro / Flash / 2.5 Pro 等较新模型通常都支持
            self.support_vision = "vision" in self._model_name or "pro" in self._model_name or "gemini-1.5" in self._model_name

        except Exception as e:
            self.LOG.error(f"初始化 Gemini 失败: {e}", exc_info=True)
            self._model = None # 标记初始化失败

    def __repr__(self):
        return 'Gemini'

    @staticmethod
    def value_check(conf: dict) -> bool:
        # 只需要 API Key 是必须的
        if conf and conf.get("api_key"):
            return True
        return False

    def _format_history(self, history: list) -> list:
        """将数据库历史消息转换为 Gemini API 的 contents 格式"""
        contents = []
        for msg in history:
            role = "model" if msg.get("sender_wxid") == self.bot_wxid else "user"
            content = msg.get('content', '')
            if content: # 避免添加空内容
                if role == "user":
                    sender_name = msg.get('sender', '未知用户')
                    # Gemini API 不直接在消息体中标记发送者，但可以在内容中包含
                    formatted_content = f"{sender_name}: {content}"
                    contents.append({'role': role, 'parts': [formatted_content]})
                else: # 模型（机器人）的消息
                    contents.append({'role': role, 'parts': [content]})
        return contents

    def get_answer(self, question: str, wxid: str, system_prompt_override=None, specific_max_history=None) -> str:
        if not self._model:
            return "Gemini 模型未成功初始化，请检查配置和网络。"

        contents = []
        # 1. 处理历史消息
        if self.message_summary and self.bot_wxid:
            history = self.message_summary.get_messages(wxid)

            limit_to_use = specific_max_history if specific_max_history is not None else self.max_history_messages
            self.LOG.debug(f"获取 Gemini 历史记录 for {wxid}, 原始条数: {len(history)}, 使用限制: {limit_to_use}")

            if limit_to_use is not None and limit_to_use > 0:
                history = history[-limit_to_use:]
            elif limit_to_use == 0:
                history = []

            self.LOG.debug(f"应用限制后 Gemini 历史条数: {len(history)}")
            contents.extend(self._format_history(history))
        else:
            self.LOG.warning(f"无法为 wxid={wxid} 获取 Gemini 历史记录。")

        # 2. 添加当前用户问题
        if question:
            contents.append({'role': 'user', 'parts': [question]})
        else:
            # 如果问题为空，可能不需要调用 API
            self.LOG.warning("尝试为 wxid={wxid} 获取答案，但问题为空。")
            # 可以返回空字符串或提示信息
            return "您没有提问哦。"


         # 3. 确定系统提示
        # 使用初始化时存储的 self._prompt 作为默认系统提示
        default_system_instruction = self._prompt if self._prompt else "You are a helpful assistant."
        effective_system_instruction = system_prompt_override if system_prompt_override else default_system_instruction
        # 添加当前时间到系统提示 (可选)
        now_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        time_mk = "\nCurrent time is: " # 加个换行
        final_system_instruction = f"{effective_system_instruction}{time_mk}{now_time}"


        rsp = ""
        try:
            # 配置生成参数 (可以从 config 中读取更多参数)
            generation_config = genai.types.GenerationConfig(
                # candidate_count=1, # 通常为 1
                # stop_sequences=["..."], # 可选的停止序列
                # max_output_tokens=2048, # 可选的最大输出 token
                temperature=0.7, # 控制随机性
                # top_p=1.0,
                # top_k=1,
            )

            self.LOG.debug(f"发送给 Gemini API 的内容条数: {len(contents)}")
            # 注意: system_instruction 在 model 初始化时已设置，这里也可以覆盖
            # 但更推荐在初始化时设置，除非需要为单次请求定制
            response = self._model.generate_content(
                contents=contents,
                generation_config=generation_config,
                # 如果需要在每次调用时覆盖，则取消注释下一行
                # system_instruction=final_system_instruction
            )

            # 处理可能的安全阻止等情况
            if response.candidates:
                 # 检查完成原因
                 finish_reason = response.candidates[0].finish_reason
                 if finish_reason == StopCandidateException.FinishReason.SAFETY:
                     rsp = "抱歉，您的请求可能包含不安全内容，已被阻止。"
                     self.LOG.warning(f"Gemini 请求被安全策略阻止 (wxid: {wxid})")
                 elif finish_reason == StopCandidateException.FinishReason.RECITATION:
                      rsp = "抱歉，回答可能包含受版权保护的内容，已被部分阻止。"
                      self.LOG.warning(f"Gemini 响应因引用保护被阻止 (wxid: {wxid})")
                 elif response.text:
                     rsp = response.text
                 else: # 其他完成原因但没有文本
                      rsp = f"生成内容时遇到问题 (完成原因: {finish_reason.name})"
                      self.LOG.error(f"Gemini 未返回文本，完成原因: {finish_reason.name} (wxid: {wxid})")

            elif response.prompt_feedback and response.prompt_feedback.block_reason:
                # 如果整个提示被阻止
                 block_reason = response.prompt_feedback.block_reason.name
                 rsp = f"抱歉，您的请求因包含不适内容而被阻止 (原因: {block_reason})。"
                 self.LOG.warning(f"Gemini 提示被阻止，原因: {block_reason} (wxid: {wxid})")
            else:
                # 未知情况，没有候选也没有提示反馈
                rsp = "抱歉，Gemini未能生成响应。"
                self.LOG.error(f"Gemini 调用成功但未返回有效响应或错误信息 (wxid: {wxid})")


        except BlockedPromptException as bpe:
             self.LOG.error(f"Gemini API 提示被阻止：{bpe}", exc_info=True)
             rsp = "抱歉，您的请求内容被 Gemini 阻止了。"
        except StopCandidateException as sce:
             self.LOG.error(f"Gemini API 响应被停止：{sce}", exc_info=True)
             rsp = "抱歉，Gemini 生成的响应包含不适内容被停止了。"
        except (GoogleAPICallError, ClientError) as api_error:
             self.LOG.error(f"Gemini API 调用错误：{api_error}", exc_info=True)
             # 尝试提供更具体的错误信息
             if "API key not valid" in str(api_error):
                  rsp = "Gemini API 密钥无效或已过期。"
             elif "quota" in str(api_error).lower():
                  rsp = "Gemini API 调用已达配额限制。"
             else:
                  rsp = f"与 Gemini 通信时出错: {type(api_error).__name__}"
        except Exception as e:
             self.LOG.error(f"调用 Gemini 时发生未知错误: {e}", exc_info=True)
             rsp = f"处理您的请求时发生未知错误: {type(e).__name__}"

        return rsp.strip() # 移除可能的首尾空白

    # 可以添加处理图片的方法
    def get_image_description(self, image_path: str, prompt: str = "请详细描述这张图片中的内容") -> str:
         if not self._model or not self.support_vision:
             return "当前 Gemini 模型未初始化或不支持图片理解。"

         if not os.path.exists(image_path):
             self.LOG.error(f"图片文件不存在: {image_path}")
             return "无法读取图片文件"

         try:
             self.LOG.info(f"使用 Gemini 分析图片: {image_path}")
             image_part = genai.types.Part.from_uri(
                 mime_type="image/jpeg", # 假设是jpeg，可以根据文件扩展名判断
                 uri=f"file://{os.path.abspath(image_path)}" # 使用文件URI
             )

             # 构建包含文本和图片的消息
             contents = [
                 {'role': 'user', 'parts': [prompt, image_part]}
             ]

             # 可以使用与 get_answer 类似的生成配置
             generation_config = genai.types.GenerationConfig(temperature=0.4)

             response = self._model.generate_content(
                 contents=contents,
                 generation_config=generation_config
             )

             # 处理响应 (与 get_answer 类似)
             # ... [省略类似的响应处理逻辑] ...
             if response.text:
                return response.text.strip()
             else:
                # ... [省略类似的错误/阻止处理逻辑] ...
                 return "Gemini 未能描述图片。"

         except Exception as e:
             self.LOG.error(f"使用 Gemini 分析图片时出错: {e}", exc_info=True)
             return f"分析图片时出错: {type(e).__name__}"

if __name__ == "__main__":
    # --- 简单的本地测试 ---
    print("运行 Gemini 本地测试...")
    logging.basicConfig(level=logging.DEBUG) # 设置日志级别

    # 模拟配置 (需要替换为你的真实 API Key)
    # 请确保从环境变量或安全途径获取 API Key，不要硬编码在代码中
    mock_config = {
        "api_key": os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY"), # 从环境变量读取，或替换为你的key
        "model_name": "gemini-1.5-flash-latest", # 使用一个快速的模型测试
        "prompt": "你是一个乐于助人的AI助手。",
        "proxy": os.environ.get("HTTP_PROXY"), # 从环境变量读取代理
        "max_history_messages": 5
    }

    if mock_config["api_key"] == "YOUR_API_KEY":
         print("警告：请设置 GEMINI_API_KEY 环境变量或替换 mock_config 中的 API Key！")
         exit()

    # 不依赖 MessageSummary 和 bot_wxid 进行简单测试
    gemini_assistant = Gemini(mock_config)

    if gemini_assistant._model: # 检查是否初始化成功
        test_question = "你好，Gemini！给我讲个关于太空旅行的笑话吧。"
        print(f"\n提问: {test_question}")
        answer = gemini_assistant.get_answer(test_question, "test_wxid")
        print(f"\nGemini 回答:\n{answer}")

        # 测试图片描述 (可选, 需要有图片)
        # image_test_path = "path/to/your/test_image.jpg"
        # if os.path.exists(image_test_path):
        #      print("\n测试图片描述...")
        #      desc_prompt = "这张图片里有什么？"
        #      description = gemini_assistant.get_image_description(image_test_path, desc_prompt)
        #      print(f"\n图片描述:\n{description}")
        # else:
        #      print(f"\n跳过图片测试，图片文件未找到: {image_test_path}")
    else:
        print("Gemini 初始化失败，无法进行测试。")
