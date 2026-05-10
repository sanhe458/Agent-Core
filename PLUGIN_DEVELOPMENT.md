# 插件开发指南

本文档详细说明了插件系统的架构、插件类型、生命周期管理以及开发规范。

## 1. 概述

### 插件系统简介

插件系统采用模块化设计，支持动态加载和卸载不同类型的插件。每个插件都是独立的功能单元，通过统一的接口与核心系统交互。

### 插件类型系统

系统支持四种插件类型，分别承担不同的职责：

| 插件类型 | 说明 | 基类 |
|---------|------|------|
| PlatformPlugin | 平台适配器，负责与外部平台通信 | PlatformPlugin |
| ToolPlugin | 工具插件，为AI提供可调用的工具能力 | ToolPlugin |
| ActionPlugin | 动作插件，执行特定业务逻辑 | ActionPlugin |
| MiddlewarePlugin | 中间件插件，在消息处理流程中插入自定义逻辑 | MiddlewarePlugin |

### 向后兼容性

系统保持向后兼容性，所有插件类型都继承自基础 `Plugin` 类，确保早期开发的插件仍能正常工作。

## 2. 插件类型详解

### 插件结构

每个插件应该包含以下文件：

```
plugins/
  plugin_name/
    __init__.py      # 插件主文件
    config.ini       # 插件配置文件
    config.ini.example # 配置文件示例（可选）
```

### PlatformPlugin（平台适配器插件）

**用途**：适配不同平台（如 QQ、Discord 等），负责接收和发送平台消息。

**必须实现的方法**：

- `on_message(message)`：接收平台原始消息
- `send_message(target, content)`：发送消息到平台

**代码示例**：

```python
from plugin_system.plugin_base import PlatformPlugin
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class MyPlatformPlugin(PlatformPlugin):
    def __init__(self, app):
        super().__init__(app)
        self.is_running = False
        self._connection = None

    async def init(self, config: Dict[str, Any]) -> None:
        logger.info("平台插件初始化")
        self.config = config

    async def start(self) -> None:
        logger.info("平台插件启动")
        self.is_running = True

    async def stop(self) -> None:
        logger.info("平台插件停止")
        self.is_running = False
        if self._connection:
            await self._connection.close()

    async def on_message(self, message: Dict[str, Any]) -> None:
        internal_message = {
            "platform": "my_platform",
            "user_id": message.get("user_id", ""),
            "session_id": message.get("session_id", ""),
            "content_type": message.get("content_type", "text"),
            "content": message.get("content", ""),
            "reply_to": message.get("reply_to"),
            "raw_message": message.get("raw_message", {})
        }
        if self.app and hasattr(self.app, 'message_pipeline'):
            await self.app.message_pipeline.process_message(internal_message)

    async def send_message(self, target: str, content: str) -> Dict[str, Any]:
        logger.info(f"发送消息到 {target}: {content[:50]}...")
        try:
            result = await self._send_to_platform(target, content)
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return {"success": False, "error": str(e)}
```

### ToolPlugin（工具插件）

**用途**：为AI提供可调用的工具能力，AI可以通过工具执行特定操作并获取结果。

**必须实现的方法**：

- `register_tool(name, description, parameters, handler)`：注册工具
- `execute_tool(tool_name, params)`：执行指定工具（由系统调用）

**工具定义格式**：

| 字段 | 说明 | 示例 |
|------|------|------|
| name | 工具名称 | "get_weather" |
| description | 工具描述 | "获取指定城市的天气信息" |
| parameters | 参数定义（JSON Schema） | 见下方示例 |
| handler | 处理函数 | async def get_weather(city: str) |

**代码示例**：

```python
from plugin_system.plugin_base import ToolPlugin
from typing import Dict, Any
import asyncio
import logging

logger = logging.getLogger(__name__)

class ExampleToolPlugin(ToolPlugin):
    def __init__(self, app):
        super().__init__(app)
        self.is_enabled = True

    async def init(self, config: Dict[str, Any]):
        logger.info("工具插件初始化中...")
        await super().init(config)
        self.is_enabled = config.get("enabled", True)

        if self.is_enabled:
            self._register_tools()

    def _register_tools(self):
        logger.info("开始注册工具...")

        self.register_tool(
            name="get_weather",
            description="获取指定城市的当前天气信息",
            parameters={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称",
                    }
                },
                "required": ["city"]
            },
            handler=self.get_weather
        )

        self.register_tool(
            name="get_time",
            description="获取当前的日期和时间",
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            },
            handler=self.get_time
        )

        logger.info(f"共注册了 {len(self._tools)} 个工具")

    async def get_weather(self, city: str) -> Dict[str, Any]:
        logger.info(f"正在获取 {city} 的天气信息...")
        await asyncio.sleep(0.1)

        return {
            "city": city,
            "temperature": 22,
            "condition": "晴",
            "humidity": 65,
            "wind_speed": "3级"
        }

    async def get_time(self) -> Dict[str, Any]:
        from datetime import datetime
        now = datetime.now()
        return {
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "timestamp": now.timestamp()
        }

    async def start(self):
        await super().start()
        logger.info("工具插件已成功启动")

    async def stop(self):
        logger.info("工具插件正在停止...")
        await super().stop()
```

### ActionPlugin（动作插件）

**用途**：执行特定业务逻辑，与 ToolPlugin 类似但更适合复杂的业务流程。

**必须实现的方法**：

- `register_action(name, description, parameters, handler)`：注册动作
- `execute_action(action_name, params)`：执行指定动作（由系统调用）

**代码示例**：

```python
from plugin_system.plugin_base import ActionPlugin
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class ExampleActionPlugin(ActionPlugin):
    def __init__(self, app):
        super().__init__(app)

    async def init(self, config: Dict[str, Any]):
        logger.info("动作插件初始化中...")
        await super().init(config)
        self._register_actions()

    def _register_actions(self):
        self.register_action(
            name="send_notification",
            description="发送通知到指定用户",
            parameters={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "用户ID"
                    },
                    "message": {
                        "type": "string",
                        "description": "通知内容"
                    }
                },
                "required": ["user_id", "message"]
            },
            handler=self.send_notification
        )

    async def send_notification(self, user_id: str, message: str) -> Dict[str, Any]:
        logger.info(f"发送通知给用户 {user_id}: {message}")
        return {
            "success": True,
            "user_id": user_id,
            "message": message,
            "sent_at": "2024-01-01 12:00:00"
        }

    async def start(self):
        await super().start()
        logger.info("动作插件已启动")

    async def stop(self):
        await super().stop()
        logger.info("动作插件已停止")
```

### MiddlewarePlugin（中间件插件）

**用途**：在消息处理流程中插入自定义逻辑，可用于消息过滤、日志记录、错误处理等。

**必须实现的方法**：

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `pre_process(message)` | 预处理消息 | 返回 None 表示拦截，返回消息继续处理 |
| `post_process(result)` | 后处理结果 | 返回处理后的结果 |
| `on_error(error, message)` | 错误处理 | 返回处理结果或抛出异常 |

**优先级说明**：

- 通过 `priority` 属性设置，数值越小优先级越高
- 默认优先级为 100
- 优先级越高的中间件越先执行 `pre_process`，越后执行 `post_process`

**代码示例**：

```python
from plugin_system.plugin_base import MiddlewarePlugin
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class ExampleMiddlewarePlugin(MiddlewarePlugin):
    def __init__(self, app):
        super().__init__(app)
        self._priority = 50
        self._blocked_words: List[str] = []
        self._verbose_logging = False

    async def init(self, config: Dict[str, Any]):
        logger.info(f"中间件插件初始化中 (优先级: {self._priority})...")

        if "general" in config:
            general_config = config["general"]
            if "priority" in general_config:
                self._priority = int(general_config["priority"])

            blocked_words_str = general_config.get("blocked_words", "")
            if blocked_words_str:
                self._blocked_words = [word.strip() for word in blocked_words_str.split(",") if word.strip()]

        if "logging" in config:
            logging_config = config["logging"]
            self._verbose_logging = logging_config.get("verbose_logging", False)

        logger.info(f"已加载 {len(self._blocked_words)} 个阻塞词")

    def pre_process(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not message:
            return message

        content = message.get("content", "")
        user_id = message.get("user_id", "unknown")

        for blocked_word in self._blocked_words:
            if blocked_word.lower() in content.lower():
                logger.info(f"消息被拦截 - 用户: {user_id}, 包含阻塞词: {blocked_word}")
                return None

        return message

    def post_process(self, result: Any) -> Any:
        logger.info(f"处理完成，结果类型: {type(result).__name__}")
        return result

    def on_error(self, error: Exception, message: Optional[Dict[str, Any]] = None) -> Any:
        user_id = message.get("user_id", "unknown") if message else "unknown"
        logger.error(f"处理错误 - 用户: {user_id}, 错误: {str(error)}")
        raise error

    async def start(self):
        logger.info(f"中间件插件已启动 (优先级: {self._priority})")

    async def stop(self):
        logger.info("中间件插件已停止")
```

## 3. 插件生命周期

### 生命周期钩子

插件从加载到卸载会经历以下阶段：

| 阶段 | 方法 | 说明 |
|------|------|------|
| 注册 | `on_register()` | 插件类实例化后调用，用于初始化配置 |
| 初始化 | `async init(config)` | 异步初始化插件资源 |
| 启动 | `async start()` | 启动插件服务 |
| 运行 | - | 插件正常工作状态 |
| 停止 | `async stop()` | 停止插件服务，清理资源 |
| 重载 | `on_config_reload()` | 配置重新加载时调用 |

**基本生命周期实现**：

```python
from plugin_system.plugin_base import Plugin
from typing import Dict, Any

class MyPlugin(Plugin):
    async def init(self, config: Dict[str, Any]):
        logger.info("插件初始化中...")
        self.config = config

    async def start(self):
        logger.info("插件启动")
        self.is_running = True

    async def stop(self):
        logger.info("插件停止")
        self.is_running = False
```

### 加载顺序

插件加载遵循以下规则：

1. 按拓扑顺序解析 `depends_on` 依赖关系
2. 依赖的插件先加载
3. 检测到循环依赖时发出警告，并按发现顺序加载
4. 加载顺序日志会输出到控制台

### 依赖管理

通过 `config.ini` 中的 `[dependencies]` 配置节声明依赖：

```ini
[dependencies]
# title: 依赖配置
# desc: 声明此插件依赖的其他插件

# title: 依赖插件
# desc: 此插件依赖的插件名称列表，逗号分隔
# type: string
depends_on = other_plugin, another_plugin
```

## 4. 配置文件格式

### INI 格式说明

插件配置使用 INI 格式，位于 `config.ini` 文件中。

### 元数据注释格式

通过 `# key: value` 格式添加配置项的元数据：

| 元数据键 | 说明 |
|---------|------|
| title | 配置项/分组的标题 |
| desc | 配置项/分组的描述 |
| type | 配置类型：bool, number, string, select, multiselect |

### 配置类型

| 类型 | 说明 | 示例 |
|------|------|------|
| bool | 布尔值 | true, false |
| number | 数值 | 8080, 3.14 |
| string | 字符串 | "hello" |
| select | 下拉选择 | option1 |
| multiselect | 多选 | option1,option2 |

### 完整配置示例

```ini
# title: 我的插件
# desc: 这是一个示例插件配置

[general]
# title: 通用配置
# desc: 插件通用设置

# title: 启用插件
# desc: 是否启用该插件
# type: bool
enabled = true

# title: 优先级
# desc: 中间件处理优先级，数值越小优先级越高
# type: number
priority = 100

# title: 阻塞词
# desc: 需要拦截的关键词列表，逗号分隔
# type: string
blocked_words =

[server]
# title: 服务器配置
# desc: 连接服务器的相关配置

# title: 主机地址
# desc: 服务器主机地址
# type: string
host = localhost

# title: 端口
# desc: 服务器端口号
# type: number
port = 8080

[logging]
# title: 日志配置
# desc: 日志输出相关配置

# title: 详细日志
# desc: 是否输出详细日志信息
# type: bool
verbose_logging = false

[dependencies]
# title: 依赖配置
# desc: 插件依赖声明

# title: 依赖插件
# desc: 此插件依赖的其他插件名称
# type: string
depends_on =
```

## 5. 消息格式

### 接收消息格式

插件收到的消息格式如下：

```python
{
    "platform": str,       # 平台名称，如 "qq"
    "user_id": str,        # 用户ID
    "session_id": str,     # 会话ID
    "content_type": str,   # 内容类型: "text", "image", "voice"
    "content": str,        # 消息内容
    "reply_to": str,       # 可选，回复目标消息ID
    "raw_message": dict    # 平台原始消息数据
}
```

### 发送消息

```python
await plugin.send_message(target, content)
```

- `target`：目标标识（用户ID或群组ID）
- `content`：消息内容

## 6. 示例插件参考

项目提供了多个示例插件供参考：

| 插件目录 | 类型 | 说明 |
|---------|------|------|
| plugins/console/ | Platform | 控制台平台插件（交互式测试） |
| plugins/qq/ | Platform | QQ 平台插件（NapCat 协议） |
| plugins/example_tool/ | Tool | 工具插件示例（天气、时间查询） |
| plugins/example_middleware/ | Middleware | 中间件插件示例（消息过滤） |

### 控制台插件 (plugins/console/)

简单的交互式控制台平台，用于测试和调试。

### QQ 插件 (plugins/qq/)

完整的 QQ 平台适配器，支持：
- WebSocket 实时消息接收
- 群组/私聊消息发送
- 动作调用（禁言、踢人等管理操作）
- 登录信息查询

### 工具插件示例 (plugins/example_tool/)

演示如何注册工具，包含：
- `get_weather`：获取城市天气
- `get_time`：获取当前时间

### 中间件插件示例 (plugins/example_middleware/)

演示中间件的使用，包含：
- 消息预处理（阻塞词过滤）
- 结果后处理
- 错误处理

## 7. 注意事项

1. **异步编程**：插件方法应尽可能使用 `async/await`，避免阻塞主线程
2. **异常处理**：插件应处理好自身异常，避免影响整个系统运行
3. **配置管理**：提供合理的配置选项，使用元数据注释提升可读性
4. **日志记录**：使用 `logging` 模块记录关键操作和错误信息
5. **资源清理**：在 `stop()` 方法中正确释放资源（连接、文件句柄等）
6. **依赖声明**：如有依赖关系，请明确声明以便正确加载
7. **类型注解**：建议添加类型注解以提升代码可读性和可维护性
