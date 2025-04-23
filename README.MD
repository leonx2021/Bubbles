# Bubbles-WechatAI
> 我叫 泡泡（Bubbles） - 一个个人微信助手

![版本](https://img.shields.io/badge/版本-1.0.0-red)
![wcferry](https://img.shields.io/badge/wcferry-39.5.1-blue)
![Python](https://img.shields.io/badge/Python-3.8+-green)
![License](https://img.shields.io/badge/License-Apache2.0-yellow)

## 📝 项目简介

Bubbles 是一个功能丰富的微信机器人框架，基于 [wcferry](https://github.com/lich0821/wcferry) 开发，支持接入多种大型语言模型（LLM），提供丰富的交互功能和定时任务。该项目旨在将微信客户端转变为一个智能的个人助手，可以执行多种实用功能，带来便捷的用户体验。

## ✨ 核心特性

### 🤖 灵活的模型配置
- 支持为不同的群聊和私聊设置不同的 AI 模型和 system prompt
  - OpenAI (ChatGPT)
  - Google Gemini
  - 智谱 AI (ChatGLM)
  - 科大讯飞星火大模型
  - 阿里云通义千问
  - TigerBot
  - DeepSeek
  - Perplexity
  - Ollama (本地部署的模型)

### 🛠️ 丰富的命令系统
- 强大的命令路由系统，让功能新增无比简单
- 支持自定义命令及参数
- 预设 [多种实用和娱乐命令](#可用命令)

### 🎨 AI 图像生成
- 支持调用多种 AI 绘图模型生成图片

### ⏰ A定时任务与提醒功能
- 每日天气预报推送
- 每日新闻资讯推送
- 工作日报/周报/月报提醒
- 个人自定义提醒系统（通过自然语言设置定时提醒）

### 📊 对话管理
- 智能消息总结功能
- 处理各类微信消息（文本、图片、小程序、链接等）

### 🔧 实用工具
- 自动接受好友请求并打招呼
- 自动响应群聊和私聊消息

## 🛠️ 安装指南

### 系统要求
- Python 3.8 或更高版本
- Windows 操作系统（wcferry 要求）
- 微信 PC 版客户端

### 安装步骤

1. **克隆仓库**
   ```bash
   git clone https://github.com/zippland/Bubbles-WechatAI.git
   cd Bubbles-WechatAI
   ```

2. **创建并激活虚拟环境（可选但推荐）**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **配置项目**
   ```bash
   # 复制配置模板
   cp config.yaml.template config.yaml
   
   # 编辑配置文件，填入您的 API 密钥等信息
   notepad config.yaml
   ```

## ⚙️ 配置说明

配置文件 `config.yaml` 包含以下主要部分：

### AI 模型配置

每个 AI 模型都有自己的配置部分，例如：

```yaml
# ChatGPT 配置
CHATGPT:
  key: "your-openai-api-key"
  base_url: "https://api.openai.com/v1"
  model: "gpt-4o-mini"  # 可选：gpt-4, gpt-3.5-turbo 等
  temperature: 0.7
  max_tokens: 2000
  system_prompt: "你是一个有用的助手。"
  proxy: "http://127.0.0.1:7890"  # 可选：如需代理请填写
```

### 群组/私聊模型映射

您可以为不同的群聊或私聊指定不同的 AI 模型：

```yaml
# 群组模型配置
GROUP_MODELS:
  # 默认模型 ID
  default: 21  # 2 代表 CHATGPT
  
  # 群聊模型映射
  mapping:
    - room_id: "12345678@chatroom"  # 群聊 ID
      model: 2  # 2 代表 CHATGPT

  # 私聊模型映射
  private_mapping:
    - wxid: "wxid_abc123"  # 用户 wxid
      model: 8  # 8 代表 Deepseek
```

### 功能开关

您可以启用或禁用各种功能：

```yaml
# 功能开关
  news_report # 每日新闻推送
  weather_report  # 每日天气推送
  report_reminder # 日报周报月报提醒
  image_generation  # AI生图
  goblin_gift # 古灵阁妖精的馈赠
  perplexity  # perplexity
```

## 🚀 使用方法

### 启动机器人

```bash
python main.py
```

### 可用命令

机器人支持多种命令，按功能分类如下：

#### 基础系统命令
- `info`、`帮助`、`指令` - 显示机器人的帮助信息
- `骂一下 @用户名` - 让机器人骂指定用户（仅群聊）
- `reset`、`重置` - 重置机器人缓存的上下文历史

#### Perplexity AI 命令
- `ask 问题内容` - 使用 Perplexity AI 进行深度查询（需@机器人）

#### 消息管理命令
- `summary`、`/总结` - 总结群聊最近的消息（仅群聊）
- `clearmessages`、`/清除历史` - 从数据库中清除群聊的历史消息记录（仅群聊）

#### 天气和新闻工具
- `天气预报 城市名`、`预报 城市名` - 查询指定城市未来几天的天气预报
- `天气 城市名`、`温度 城市名` - 查询指定城市的当前天气
- `新闻` - 获取最新新闻

#### 决斗系统命令
- `决斗 @用户名` - 发起决斗（仅群聊）
- `偷袭 @用户名`、`偷分 @用户名` - 偷袭其他玩家（仅群聊）
- `决斗排行`、`决斗排名`、`排行榜` - 查看决斗排行榜（仅群聊）
- `决斗战绩`、`我的战绩`、`战绩查询` - 查看决斗战绩（仅群聊）
- `我的装备`、`查看装备` - 查看自己的装备（仅群聊）
- `改名 旧名称 新名称` - 更改昵称（仅群聊）

#### 成语系统命令
- `#成语` 或 `?成语` 或 `？成语` - 成语接龙与查询

#### 提醒功能
- `提醒xxxxx` - 用自然语言设置一个提醒
- `查看提醒`、`我的提醒`、`提醒列表` - 查看您设置的所有提醒
- `删除提醒 ID:xxxx`、`取消提醒 all` - 删除指定的（或所有）提醒

## 🎮 游戏功能详解

### 决斗系统

Bubbles 内置了一个有趣的决斗游戏系统，用户可以在群聊中挑战其他成员：

- **开始决斗**：使用 `决斗 @用户` 开始一场决斗
- **偷袭玩家**：使用 `偷袭 @用户` 偷袭其他玩家
- **查看排名**：使用 `决斗排行` 查看全服决斗排行榜
- **个人统计**：使用 `决斗战绩` 查看个人决斗数据
- **查看装备**：使用 `我的装备` 查看自己当前的装备
- **更改名称**：使用 `改名 旧名称 新名称` 更改自己在决斗系统中的显示名称

### 成语接龙

使用 `#成语` 来查询成语或参与成语接龙游戏。还可以使用 `?成语` 查询成语的详细释义。

### 古灵阁妖精馈赠

这是一个随机事件系统，机器人会在聊天中随机触发"古灵阁妖精馈赠"事件，为用户提供惊喜奖励。

## 📋 项目结构

```
Bubbles-WechatAI/
├── ai_providers/       # AI 模型接口实现
├── commands/           # 命令系统实现
├── data/               # 数据文件
├── function/           # 功能模块
│   ├── func_chengyu.py     # 成语功能
│   ├── func_duel.py        # 决斗功能
│   ├── func_news.py        # 新闻功能
│   ├── func_weather.py     # 天气功能
│   └── ...
├── image/              # 图像生成相关
├── logs/               # 日志目录
├── config.yaml         # 配置文件
├── config.yaml.template # 配置模板
├── constants.py        # 常量定义
├── main.py             # 入口文件
├── robot.py            # 机器人核心实现
└── requirements.txt    # 项目依赖
```

## 🤝 贡献指南

欢迎对本项目做出贡献！您可以通过以下方式参与：

1. **报告问题**：提交 issue 报告 bug 或提出功能建议
2. **提交代码**：通过 Pull Request 提交您的改进
3. **完善文档**：帮助改进项目文档

## 📄 许可证

本项目采用 Apache 2.0 许可证，详情请参阅 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- [wcferry](https://github.com/lich0821/wcferry) - 提供微信机器人底层支持
- 所有贡献者和用户

## ❓ 常见问题

**Q: 如何获取群聊 ID？**
A: 在群聊中发送一条消息，机器人日志会显示该消息的来源群聊 ID。

**Q: 如何添加新的 AI 模型？**
A: 在 `ai_providers` 目录下创建新的模型接口实现，然后在 `robot.py` 中注册该模型。

**Q: 出现 "AI 模型未响应" 错误怎么办？**
A: 检查相应 AI 模型的 API 密钥配置和网络连接，确保 API 可访问。

**Q: 机器人不回复消息怎么办？**
A: 检查 wcferry 服务是否正常运行，查看日志文件了解详细错误信息。

## 📞 联系方式

如有任何问题或建议，请通过以下方式联系我们：

- GitHub Issues: [提交问题](https://github.com/zippland/Bubbles-WechatAI/issues)
- Email: zylanjian@example.com

---

**注意**：本项目仅供学习和个人使用，请遵守微信使用条款，不要用于任何违反法律法规的活动。
