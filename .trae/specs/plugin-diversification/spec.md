# 插件系统多元化优化规格说明

## Why
当前的插件系统仅作为平台适配器使用（QQ、Console），限制了插件系统的扩展性。AI需要更多能力，如工具调用、动作执行、消息预处理/后处理等，应该让插件系统支持多元化插件类型。

## What Changes

### 1. 插件类型体系重构
- 新增 `PlatformPlugin`: 平台适配器插件（原有功能，保持向后兼容）
- 新增 `ToolPlugin`: 工具插件，为AI提供可调用的工具能力
- 新增 `ActionPlugin`: 动作插件，执行特定业务逻辑
- 新增 `MiddlewarePlugin`: 中间件插件，在消息处理流程中插入自定义逻辑
- 保留原有 `Plugin` 基类作为所有插件的共同基类

### 2. 插件生命周期扩展
- 新增 `get_type()` 方法标识插件类型
- 新增 `get_capabilities()` 方法让插件声明自己的能力
- 新增 `on_register()` 插件注册时调用
- 插件现在支持懒加载（lazy_load配置项）

### 3. 工具插件能力
- 工具插件可声明 `tools` 属性，AI可调用
- 工具定义包含: name, description, parameters schema
- 工具可同步或异步执行

### 4. 中间件插件能力
- 可在消息处理流程的不同阶段介入
- 支持 `pre_process`, `post_process`, `on_error` 钩子
- 支持修改消息内容或阻断处理流程

### 5. 动作插件能力
- 注册 `actions` 字典，定义可执行的动作
- 支持参数验证和执行结果返回
- 可被其他插件或AI触发

### 6. 插件管理器增强
- 新增 `get_plugins_by_type()` 方法按类型获取插件
- 新增 `get_all_tools()` 方法获取所有工具
- 新增 `execute_tool()` 执行指定工具
- 新增 `execute_action()` 执行指定动作
- 支持插件依赖声明和加载顺序控制

## Impact
- Affected specs: 插件系统核心能力
- Affected code:
  - `plugin_system/plugin_base.py` - 重构基类
  - `plugin_system/plugin_manager.py` - 增强管理器
  - `PLUGIN_DEVELOPMENT.md` - 更新文档

## ADDED Requirements

### Requirement: 插件类型系统
系统 SHALL 支持多种插件类型: PlatformPlugin, ToolPlugin, ActionPlugin, MiddlewarePlugin

#### Scenario: 加载不同类型插件
- **WHEN** 插件管理器加载 plugins 目录下的插件
- **THEN** 根据插件的 `get_type()` 返回值将其分类到对应的类型集合

### Requirement: 工具插件能力
系统 SHALL 提供工具插件注册和执行能力

#### Scenario: 注册工具
- **WHEN** 工具插件初始化时声明 tools 属性
- **THEN** 插件管理器将其收集到全局工具列表

#### Scenario: 调用工具
- **WHEN** AI 或其他组件调用 `execute_tool(tool_name, parameters)`
- **THEN** 插件管理器找到对应插件执行并返回结果

### Requirement: 中间件插件能力
系统 SHALL 支持中间件插件在消息处理流程中插入自定义逻辑

#### Scenario: 消息预处理
- **WHEN** 中间件插件实现了 `pre_process` 方法
- **THEN** 消息管道在处理前调用该方法，可修改消息或返回短路响应

### Requirement: 动作插件能力
系统 SHALL 支持动作插件注册可执行动作

#### Scenario: 注册动作
- **WHEN** 动作插件初始化时声明 actions 属性
- **THEN** 插件管理器将其收集到全局动作列表

### Requirement: 插件依赖管理
系统 SHALL 支持插件声明依赖关系并按正确顺序加载

#### Scenario: 依赖解析
- **WHEN** 插件A声明 depends_on = ["B"]
- **THEN** 插件B将在插件A之前加载

## MODIFIED Requirements

### Requirement: Plugin 基类
原有的 `Plugin` 基类 SHALL 改为所有插件的共同基类，提供通用方法，默认实现空操作

#### Scenario: 向后兼容
- **WHEN** 现有插件（QQPlugin, ConsolePlugin）加载时
- **THEN** 无需修改代码即可正常工作

