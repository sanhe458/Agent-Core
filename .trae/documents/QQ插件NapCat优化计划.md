# QQ 插件 NapCat 适配器优化计划

## 1. 摘要

**目标**：参照 [MaiBot-Napcat-Adapter](https://github.com/Mai-with-u/MaiBot-Napcat-Adapter) 项目，重构并优化本项目的 QQ 插件，使其能够正常且完整地与 NapCat / OneBot v11 对接工作。

**当前状态**：现有 QQ 插件存在架构错误（作为服务器而非客户端运行）、消息处理不完整、缺少核心 API 等问题。

**目标状态**：实现完整的 NapCat WebSocket 客户端功能，支持全部 OneBot v11 API，实现消息收发、API 调用、心跳检测、自动重连等核心功能。

---

## 2. 当前问题分析

### 2.1 架构问题
| 问题 | 现状 | 期望 |
|------|------|------|
| WebSocket 角色 | 作为 Server (`Server.serve()`) 监听连接 | 作为 Client 主动连接 NapCat |
| 连接方向 | NapCat → 本项目 | 本项目 → NapCat |

### 2.2 功能缺失
- 缺少完整的 OneBot 消息段解析（text、image、at、reply 等）
- 缺少 OneBot action 调用机制（echo 响应匹配）
- 缺少心跳检测和超时处理
- 缺少自动重连机制
- 缺少 API 调用超时处理

---

## 3. 实施计划

### 阶段一：基础设施重构

#### 1. 添加 aiohttp 依赖
**文件**: `requirements.txt`
```
aiohttp>=3.9.0
```
**原因**: 参考项目使用的 aiohttp 库提供更稳定的 WebSocket 客户端功能

#### 2. 创建 NapCat 客户端传输层
**文件**: `plugins/qq/transport.py`（新建）
```
核心功能:
- WebSocket 客户端连接管理
- action 调用与 echo 响应匹配
- 心跳机制（发送 ping，保持连接活跃）
- 自动重连（断开后按配置延迟重连）
- 后台任务管理
```

#### 3. 创建消息编解码器
**文件**: `plugins/qq/codec.py`（新建）
```
核心功能:
- OneBot 消息段解析（CQ 码转换）
- 接收消息转换（NapCat → 内部格式）
- 发送消息转换（内部格式 → NapCat）
- 消息 ID 回显处理
```

#### 4. 创建事件路由器
**文件**: `plugins/qq/router.py`（新建）
```
核心功能:
- 消息事件分发 (message)
- 通知事件分发 (notice)
- 元事件分发 (meta_event)
- 运行时状态缓存管理
```

#### 5. 创建 API 服务层
**文件**: `plugins/qq/action_service.py`（新建）
```
核心功能:
- System API: 登录、状态、凭证、系统控制 (23个)
- Account API: 资料、好友、收藏、OCR、账号能力 (27个)
- Group API: 群、频道、公告、群管理 (41个)
- Message API: 消息、互动、转发、AI 语音 (28个)
- File API: 文件、群文件、在线文件、相册、流式传输 (43个)
```

### 阶段二：核心插件重构

#### 6. 重写 QQPlugin 主类
**文件**: `plugins/qq/__init__.py`（重写）

**主要改动**:
```python
class QQPlugin(Plugin):
    # 删除: WebSocket 服务器相关
    # 删除: message_queue 消息队列

    # 新增:
    - transport: NapCatTransportClient  # WebSocket 客户端
    - event_router: NapCatEventRouter   # 事件路由
    - action_service: NapCatActionService # API 服务
```

**新增方法**:
- `on_napcat_connected()`: NapCat 连接成功回调
- `on_napcat_disconnected()`: NapCat 断开回调
- `call_napcat_action()`: 调用 OneBot action

### 阶段三：配置优化

#### 7. 更新配置文件
**文件**: `plugins/qq/config.ini` 和 `config/config.yaml`

**新增配置项**:
```ini
[server]
host = localhost        # NapCat 服务器地址
port = 3000             # NapCat WebSocket 端口 (修改默认值)
token =                 # NapCat 访问令牌
reconnect_delay = 5     # 重连延迟（秒）
heartbeat_interval = 30 # 心跳间隔（秒）
action_timeout = 30     # API 调用超时（秒）

[message]
group_list = []         # 允许的群列表（空=全部）
private_list = []       # 允许的私聊列表（空=全部）
ban_user_id = []        # 屏蔽的用户 ID
```

### 阶段四：依赖项更新

#### 8. 更新 requirements.txt
```diff
+ aiohttp>=3.9.0
```

---

## 4. 文件结构

```
plugins/qq/
├── __init__.py           # 主插件类（重写）
├── config.ini            # 配置文件（扩展）
├── transport.py          # WebSocket 传输层（新建）
├── codec.py              # 消息编解码器（新建）
├── router.py             # 事件路由器（新建）
├── action_service.py     # OneBot API 服务（新建）
├── constants.py          # 常量定义（新建）
└── types.py              # 类型定义（新建）
```

---

## 5. API 实现清单

### 5.1 System API (23个)
| Action | 说明 |
|--------|------|
| get_login_info | 获取登录信息 |
| get_version_info | 获取版本信息 |
| get_status | 获取运行状态 |
| set_qq_profile | 设置个人资料 |
| set_self_status | 设置在线状态 |
| clean_cache | 清理缓存 |
| ... | (共23个) |

### 5.2 Account API (27个)
| Action | 说明 |
|--------|------|
| get_stranger_info | 获取陌生人信息 |
| get_friend_list | 获取好友列表 |
| get_friend_info | 获取好友信息 |
| get_stranger_info | 获取陌生人信息 |
| ... | (共27个) |

### 5.3 Group API (41个)
| Action | 说明 |
|--------|------|
| get_group_list | 获取群列表 |
| get_group_info | 获取群信息 |
| get_group_member_list | 获取群成员列表 |
| get_group_member_info | 获取群成员信息 |
| send_group_msg | 发送群消息 |
| send_group_forward_msg | 发送群合并转发 |
| ... | (共41个) |

### 5.4 Message API (28个)
| Action | 说明 |
|--------|------|
| send_msg | 发送消息 |
| send_private_msg | 发送私聊消息 |
| send_group_msg | 发送群消息 |
| delete_msg | 撤回消息 |
| get_msg | 获取消息 |
| get_forward_msg | 获取合并转发内容 |
| ... | (共28个) |

### 5.5 File API (43个)
| Action | 说明 |
|--------|------|
| get_group_file_url | 获取群文件链接 |
| upload_group_file | 上传群文件 |
| upload_group_file_async | 异步上传群文件 |
| ... | (共43个) |

---

## 6. 核心流程

### 6.1 连接流程
```
1. 插件启动 (start)
2. 创建 NapCatTransportClient
3. 配置服务器参数 (host, port, token)
4. 启动连接循环
   ├── 建立 WebSocket 连接
   ├── 认证（Bearer Token）
   ├── 启动心跳任务
   ├── 进入接收循环
   └── 异常断开 → 等待重连延迟 → 重新连接
```

### 6.2 消息接收流程
```
NapCat WebSocket
    ↓
接收 JSON 消息
    ↓
解析 post_type:
├── message → 消息处理 → on_message → message_pipeline
├── notice → 通知处理 → 日志记录
└── meta_event → 元事件 → 心跳处理
```

### 6.3 消息发送流程
```
message_pipeline.send_message()
    ↓
plugin.send_message(target, content)
    ↓
call_napcat_action("send_msg", {...})
    ↓
transport.call_action()
    ↓
发送 WebSocket 请求
等待 echo 响应
    ↓
返回发送结果
```

---

## 7. 验证步骤

### 7.1 单元测试
```bash
# 测试 WebSocket 连接
# 测试消息编解码
# 测试 API 调用
```

### 7.2 集成测试
1. 启动 NapCat（确保在运行）
2. 启动本项目
3. 验证连接成功日志
4. 发送测试消息
5. 验证消息收发正常

### 7.3 日志检查
```
[QQ] NapCat 适配器已连接: ws://localhost:3000
[QQ] 收到消息: {"post_type": "message", ...}
[QQ] 回复已发送到 qq: 123456
```

---

## 8. 实施顺序

1. **requirements.txt** - 添加 aiohttp 依赖
2. **plugins/qq/types.py** - 定义类型
3. **plugins/qq/constants.py** - 定义常量
4. **plugins/qq/codec.py** - 消息编解码
5. **plugins/qq/transport.py** - 传输层
6. **plugins/qq/router.py** - 事件路由
7. **plugins/qq/action_service.py** - API 服务
8. **plugins/qq/__init__.py** - 主插件类
9. **plugins/qq/config.ini** - 更新配置
10. **config/config.yaml** - 更新配置

---

## 9. 假设与决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| WebSocket 库 | aiohttp | 参考项目使用，稳定可靠 |
| API 范围 | 完整 164 个 API | 用户明确需求 |
| 消息格式 | OneBot v11 兼容 | NapCat 标准协议 |
| 重连策略 | 指数退避（最大5次） | 防止频繁重连 |
