# 微信机器人 2.0

🤖 全新架构的智能微信机器人，基于 LangGraph + 事件驱动 + 插件系统

## ✨ 特性

- 🧠 **多AI模型支持**: ChatGPT、DeepSeek、Gemini、Perplexity
- 🔌 **插件系统**: 可扩展的插件架构
- ⚡ **事件驱动**: 异步事件总线，松耦合设计
- 🎯 **状态管理**: 基于 LangGraph 的消息处理状态机
- ⚙️ **配置驱动**: YAML 配置文件，灵活配置
- 📊 **完整日志**: 结构化日志，便于调试
- 🔄 **定时任务**: 支持定时推送功能

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 创建配置文件

```bash
python main.py --create-config
```

### 3. 编辑配置

编辑 `config.yaml` 文件，填入你的 AI API 密钥和其他配置。

### 4. 启动机器人

```bash
python main.py
```

## 📁 项目结构

```
├── bot/                    # 机器人核心
│   ├── wechat_bot.py      # 主机器人类
│   ├── config.py          # 配置管理
│   ├── events.py          # 事件系统
│   ├── message_processor.py  # 消息处理器
│   ├── ai_manager.py      # AI管理器
│   └── plugin_manager.py  # 插件管理器
├── plugins/                # 插件目录
│   ├── weather_plugin.py  # 天气插件
│   └── news_plugin.py     # 新闻插件
├── main.py                # 启动入口
├── config.yaml            # 配置文件
└── requirements.txt       # 依赖列表
```

## 🔧 配置说明

### AI 模型配置

```yaml
ai_models:
  chatgpt:
    enabled: true
    api_key: "your_api_key"
    base_url: "https://api.openai.com/v1"
    model: "gpt-3.5-turbo"
    temperature: 0.7
```

### 群组配置

```yaml
groups:
  "group_id":
    name: "群名称"
    enabled: true
    ai_model: "chatgpt"
    max_history: 50
```

### 插件配置

```yaml
plugins_enabled:
  - "weather_plugin"
  - "news_plugin"
```

## 🔌 开发插件

### 1. 创建插件文件

在 `plugins/` 目录下创建 `.py` 文件。

### 2. 继承插件基类

```python
from bot.plugin_manager import CommandPlugin, PluginInfo

class MyPlugin(CommandPlugin):
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            name="my_plugin",
            version="1.0.0",
            description="我的插件",
            author="我"
        )
    
    def get_commands(self) -> Dict[str, Callable]:
        return {
            "hello": self._handle_hello
        }
    
    def _handle_hello(self, event_data: Dict) -> None:
        # 处理命令逻辑
        pass
```

### 3. 在配置中启用

```yaml
plugins_enabled:
  - "my_plugin"
```

## 📝 命令行选项

```bash
python main.py [选项]

选项:
  -c, --config CONFIG    配置文件路径 (默认: config.yaml)
  -l, --log-level LEVEL  日志级别 (DEBUG/INFO/WARNING/ERROR)
  --create-config        创建默认配置文件
```

## 🎯 核心概念

### 事件系统

机器人使用事件驱动架构，主要事件类型：

- `MESSAGE_RECEIVED`: 收到消息
- `AI_RESPONSE`: AI响应生成
- `COMMAND_MATCHED`: 命令匹配
- `ERROR_OCCURRED`: 错误发生

### 状态机

消息处理使用 LangGraph 状态机：

1. **接收** → 2. **分析** → 3. **路由** → 4. **处理** → 5. **响应**

### 插件类型

- **CommandPlugin**: 命令插件
- **EventPlugin**: 事件处理插件  
- **ScheduledPlugin**: 定时任务插件

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License