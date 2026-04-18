# 插件开发指南

## 插件结构

每个插件应该包含以下文件：

```
plugins/
  plugin_name/
    __init__.py      # 插件主文件
    config.ini        # 插件配置文件
    config.ini.example # 配置文件示例
```

## 插件基类

插件必须继承 `Plugin` 基类并实现以下方法：

```python
from plugin_system.plugin_base import Plugin

class MyPlugin(Plugin):
    async def init(self, config):
        """初始化插件"""
        pass
    
    async def start(self):
        """启动插件"""
        pass
    
    async def stop(self):
        """停止插件"""
        pass
    
    async def on_message(self, message):
        """接收平台原始消息"""
        pass
    
    async def send_message(self, target, content):
        """发送消息到平台"""
        pass
```

## 消息格式

### 接收消息格式

```python
{
    "platform": str,      # 平台名称，如 "qq"
    "user_id": str,       # 用户ID
    "session_id": str,    # 会话ID
    "content_type": str,  # 内容类型: "text", "image", "voice"
    "content": str,       # 消息内容
    "reply_to": str       # 可选，回复目标
}
```

### 发送消息

```python
await plugin.send_message(target, content)
```

## 配置文件

插件配置文件使用 INI 格式，可以包含元数据注释：

```ini
# title: 插件名称
# desc: 插件描述

[general]
# title: 通用配置
# desc: 插件通用设置

# title: 启用插件
# desc: 是否启用该插件
# type: bool
enabled = true

# title: 端口
# desc: 插件监听端口
# type: number
port = 8080
```

## 示例插件

参考 `plugins/console/` 和 `plugins/qq/` 目录下的示例插件。

## 注意事项

1. 插件应该是异步的，避免阻塞主线程
2. 插件应该处理好异常，确保不会影响整个系统
3. 插件应该提供合理的配置选项
4. 插件应该遵循项目的代码风格和命名规范