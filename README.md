# Agent Core

AI 仿人类程序核心框架

## 项目结构

- `core/` - 核心应用类
- `config_manager/` - 配置管理器
- `ai_model_manager/` - AI 模型管理器
- `message_pipeline/` - 消息处理管道
- `plugin_system/` - 插件系统
- `plugins/` - 插件目录
- `webui/` - Web 界面
- `config/` - 配置文件

## 功能特性

- 支持多种 AI 模型提供商（OpenAI、Ollama）
- 插件化架构，易于扩展
- Web 界面管理
- 消息处理管道
- 会话管理
- 配置热重载

## 安装

```bash
pip install -r requirements.txt
```

## 运行

```bash
python main.py
```

## 配置

修改 `config/` 目录下的配置文件：
- `config.yaml` - 主配置文件
- `models.yaml` - 模型配置文件

## 插件开发

参考 `PLUGIN_DEVELOPMENT.md` 文档

## 许可证

MIT License