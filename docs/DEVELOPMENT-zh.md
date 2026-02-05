
# 开发指南 (Development Guide)

本文档是 **CC Switch** 的详细开发指南，面向想要参与项目开发、维护或扩展的开发者。

## 目录

- [项目架构](#项目架构)
- [开发环境搭建](#开发环境搭建)
- [代码规范](#代码规范)
- [项目结构详解](#项目结构详解)
- [核心流程](#核心流程)
- [调试指南](#调试指南)
- [添加新功能](#添加新功能)
- [数据库管理](#数据库管理)
- [测试](#测试)
- [部署指南](#部署指南)
- [API 文档](#api-文档)
- [故障排查](#故障排查)
- [贡献指南](#贡献指南)

---

## 🏗️ 项目架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        Claude Code                           │
│                   (客户端 / CLI 工具)                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              CC Switch                         │
├─────────────────────┬───────────────────────────────────────┤
│    前端 (Frontend)   │            后端 (Backend)              │
│                     │                                       │
│  ┌───────────────┐  │  ┌─────────────────────────────────┐  │
│  │  Svelte 5     │  │  │     FastAPI + Uvicorn          │  │
│  │  TypeScript   │  │  │                                 │  │
│  │  PWA          │  │  │  ┌───────────────────────────┐  │  │
│  │               │  │  │  │   API 路由层              │  │  │
│  │  - 聊天界面   │  │  │  │  - /v1/messages           │  │  │
│  │  - 管理面板   │  │  │  │  - /api/providers         │  │  │
│  │  - 健康监控   │  │  │  │  - /api/health            │  │  │
│  │  - 设置页面   │  │  │  │  - /api/stats             │  │  │
│  └───────────────┘  │  │  └───────────────────────────┘  │  │
│                     │  │                                 │  │
│  ┌───────────────┐  │  │  ┌───────────────────────────┐  │  │
│  │   WebSocket   │  │  │  │    服务层 (Services)      │  │  │
│  │   实时通信    │  │  │  │                           │  │  │
│  └───────────────┘  │  │  │  - MessageService         │  │  │
│                     │  │  │  - ProviderService        │  │  │
└─────────────────────┴──┴──┴───────────────────────────┴──┘
                        │                                   │
                        ▼                                   ▼
              ┌─────────────────┐                  ┌──────────────────┐
              │   浏览器存储    │                  │    数据层        │
              │   (localStorage)│                  │                  │
              └─────────────────┘                  │  ┌────────────┐ │
                                                 │  │ SQLite DB  │ │
                                                 │  └────────────┘ │
                                                 │                  │
                                                 │  ┌────────────┐ │
                                                 │  │ 连接池管理  │ │
                                                 │  └────────────┘ │
                                                 └──────────────────┘
```

### 后端架构 (Backend)

后端基于 **FastAPI** 框架，采用分层架构设计：

#### 目录结构

```
backend/app/
├── routes/                  # API 路由
│   ├── messages.py          # 消息 API（兼容 Anthropic）
│   ├── health.py            # 健康检查路由
│   ├── auth.py              # 认证路由
│   ├── oauth.py             # OAuth 路由
│   └── ...
├── services/                # 业务逻辑层
│   ├── message_service.py   # 消息处理
│   ├── provider_service.py  # 供应商管理
│   ├── auth_service.py      # 认证服务
│   ├── health_service.py    # 健康监控
│   ├── token_counter.py     # Token 计数
│   └── ...
├── converters/              # 格式转换器
│   ├── anthropic_to_openai.py
│   ├── openai_to_anthropic.py
│   └── streaming_format.py
├── infrastructure/          # 基础设施服务
│   ├── cache.py             # 内存/Redis 缓存
│   └── telemetry.py         # OpenTelemetry 集成
├── database/                # 数据访问层（异步 SQLite）
│   ├── core.py              # 数据库连接和 schema
│   ├── users.py             # 用户管理
│   ├── api_keys.py          # API Key 存储
│   ├── conversations.py     # 对话和消息
│   ├── request_logs.py      # 请求日志
│   ├── token_usage.py       # Token 使用统计
│   ├── health_history.py    # 健康历史
│   ├── config_changes.py    # 配置变更历史
│   ├── oauth_accounts.py    # OAuth 账户关联
│   └── encryption.py        # 加密工具
├── utils/                   # 工具函数
│   ├── token_extractor.py   # 统一 Token 提取（支持 OpenAI/Anthropic）
│   ├── security_utils.py    # 加密、验证、API Key 脱敏
│   ├── color_logger.py      # 彩色日志
│   ├── error_handler.py     # 错误响应格式化
│   └── response.py          # 响应工具
└── encryption_key.py        # 加密密钥管理
```

#### 核心组件

**1. API 层 (`/api/`)**
- 暴露 RESTful API 端点
- 处理 HTTP 请求/响应
- 验证请求参数
- JWT 认证

**2. 服务层 (`/services/`)**
- 业务逻辑处理
- 供应商请求转发
- 故障转移处理
- 并发控制

**3. 数据层 (`/database/`)**
- SQLite 数据库 + 连接池
- 异步数据访问
- 数据加密存储
- 请求日志记录

**4. 转换层 (`/converters/`)**
- Anthropic ↔ OpenAI 格式转换
- 流式响应处理
- 工具调用格式转换

### 前端架构 (Frontend)

前端基于 **Svelte 5** 框架，采用现代化响应式设计：

#### 目录结构

```
frontend/src/
├── lib/
│   ├── components/            # 可复用的 Svelte 组件
│   │   ├── chat/              # 聊天相关组件（ChatArea、MessageBubble 等）
│   │   ├── layout/            # 布局组件（Header、MobileNav）
│   │   ├── providers/         # 供应商管理组件
│   │   ├── settings/          # 设置组件
│   │   ├── ui/                # 基础 UI 组件（Button、Input、Card 等）
│   │   ├── i18n/              # 国际化组件（Translate）
│   │   ├── ErrorMessageModal.svelte
│   │   ├── Pagination.svelte
│   │   ├── ProviderForm.svelte
│   │   ├── SettingsModal.svelte
│   │   ├── WelcomeModal.svelte
│   │   └── OAuthIcon.svelte
│   ├── services/              # API 客户端服务
│   │   ├── api.ts             # 主 API 客户端
│   │   ├── chatService.ts     # 聊天服务
│   │   ├── auth.ts            # 认证服务
│   │   ├── permissions.ts     # 权限管理服务
│   │   ├── oauthProviders.ts  # OAuth 供应商配置
│   │   ├── apiKeys.ts         # API Key 服务
│   │   ├── apiKeyStorage.ts   # 安全 API Key 存储
│   │   ├── providers.ts       # 供应商服务
│   │   ├── health.ts          # 健康监控服务
│   │   ├── stats.ts           # 统计服务
│   │   ├── config.ts          # 配置服务
│   │   └── preferences.ts     # 用户偏好服务
│   ├── stores/                # Svelte store（Svelte 5 $state）
│   │   ├── auth.svelte.ts     # 认证状态
│   │   ├── chatSession.ts     # 聊天会话状态
│   │   ├── providers.ts       # 供应商状态
│   │   ├── health.ts          # 健康状态
│   │   ├── language.ts        # 国际化状态
│   │   ├── theme.ts           # 主题状态
│   │   ├── toast.ts           # 提示消息状态
│   │   └── config.ts          # 配置状态
│   ├── types/                 # TypeScript 类型定义
│   │   ├── permission.ts      # 权限类型
│   │   ├── apiKey.ts          # API Key 类型
│   │   ├── provider.ts        # 供应商类型
│   │   ├── health.ts          # 健康类型
│   │   ├── config.ts          # 配置类型
│   │   └── language.ts        # 语言类型
│   ├── config/                # 配置文件
│   │   └── keyboardShortcuts.ts  # 键盘快捷键
│   ├── utils/                 # 工具函数
│   │   ├── gesture.ts         # 手势检测
│   │   └── session.ts         # 会话管理
│   └── i18n/                  # 国际化资源（16 种语言）
├── routes/                    # SvelteKit 页面
│   ├── +layout.svelte         # 根布局（认证和权限检查）
│   ├── +page.svelte           # 首页
│   ├── login/                 # 登录页（邮箱 + OAuth）
│   │   └── +page.ts
│   ├── chat/                  # 聊天页面
│   ├── providers/             # 供应商管理
│   ├── api-keys/              # API Key 管理
│   ├── health/                # 健康监控
│   ├── stats/                 # 使用统计
│   ├── config/                # 系统配置
│   ├── admin/
│   │   └── users/             # 用户管理
│   │       ├── +page.svelte   # 用户列表
│   │       └── [id]/          # 用户详情和权限配置
│   └── oauth/
│       └── [provider]/        # OAuth 回调处理
│           └── callback/      # OAuth 回调页面
└── app.html                   # HTML 模板
```

#### 核心特性

**1. 响应式状态管理**
- Svelte 5 原生 `$state()` 和 `$derived()`
- 可组合的状态管理（类似 React hooks）
- 细粒度响应式更新

**2. 服务层架构**
- 统一的 API 客户端 (`api.ts`)
- 分离关注点：认证、聊天、配置等
- 错误处理和重试机制

**3. 状态管理**
- Svelte Store 轻量级状态管理
- 类型安全的 TypeScript 定义
- 持久化存储（localStorage）

**4. 国际化 (i18n)**
- 16种语言支持
- JSON 格式翻译文件
- 自动语言检测和切换

### 数据库设计

使用 SQLite 数据库存储所有数据：

#### 核心表结构

**1. 用户表 (`users`)**
```sql
- id (主键)
- email (唯一)
- password_hash
- name
- language (用户语言偏好)
- is_admin
- is_active
- created_at
- updated_at
- last_login_at
```

**2. API Key 表 (`api_keys`)**
```sql
- id (主键)
- key_hash (唯一)
- key_prefix
- encrypted_key (加密存储)
- name
- email
- user_id (外键)
- is_active
- last_used_at
- created_at
- updated_at
```

**3. 对话表 (`conversations`)**
```sql
- id (主键)
- user_id (外键)
- title
- provider_name
- api_format
- model
- created_at
- updated_at
```

**4. 消息表 (`conversation_messages`)**
```sql
- id (主键)
- conversation_id (外键)
- role (user/assistant/system)
- content
- provider_name
- model
- input_tokens
- output_tokens
- thinking (思考过程)
- created_at
```

**5. 请求日志表 (`request_logs`)**
```sql
- id (主键)
- request_id
- provider_name
- model
- request_params
- response_data
- status_code
- error_message
- input_tokens
- output_tokens
- response_time_ms
- created_at
- indexed_at
```

### API 设计

#### 核心端点

**1. 消息 API (兼容 Anthropic)**
- `POST /v1/messages` - 发送消息
- `POST /v1/messages/stream` - 流式消息

**2. 供应商管理**
- `GET /api/providers` - 获取供应商列表
- `POST /api/providers` - 添加供应商
- `PUT /api/providers/{id}` - 更新供应商
- `DELETE /api/providers/{id}` - 删除供应商

**3. 健康检查**
- `GET /health` - 基础健康检查
- `GET /api/health` - 详细健康信息
- `POST /api/health/check` - 手动触发检查

**4. 统计信息**
- `GET /api/stats/token-usage` - Token 使用统计
- `GET /api/stats/requests` - 请求统计
- `GET /api/stats/providers` - 供应商统计

**5. 对话管理**
- `GET /api/conversations` - 获取对话列表
- `POST /api/conversations` - 创建对话
- `GET /api/conversations/{id}` - 获取对话详情
- `DELETE /api/conversations/{id}` - 删除对话
- `GET /api/conversations/{id}/messages` - 获取消息列表

## 🚀 核心功能

### 🔥 高性能架构

- **异步数据库** - aiosqlite + 连接池，消除阻塞，提升并发能力 10-100 倍
- **HTTP 连接池优化** - 支持 10k QPS，Keepalive 连接优化
- **多级缓存架构** - L1（内存）+ L2（Redis）缓存，显著提升响应速度

### 🛡️ 企业级安全

- **JWT 密钥强制管理** - 生产环境必须配置，否则生成临时密钥并警告
- **加密密钥管理** - ENCRYPTION_KEY 支持，敏感数据加密存储
- **强密码策略** - 至少 12 字符，管理员密码检查

### 🌍 国际化支持

- **16种语言支持** - 中文、English、日本語、한국어、Français、Español、Deutsch、Русский、Português、Italiano、Nederlands、العربية、हिन्दी、ไทย、Tiếng Việt、Bahasa Indonesia
- **智能语言切换** - 自动检测浏览器语言，支持手动切换
- **完整UI翻译** - 所有页面、表单、按钮、提示信息完全本地化
- **本地化存储** - 智能记忆用户语言偏好

### 🌐 现代管理界面

- **Svelte 5 + TypeScript** - 现代化前端框架，全新响应式系统，类型安全
- **PWA 支持** - 离线访问、安装到主屏幕、后台同步
- **深色/浅色主题** - 用户体验优化
- **代码分割** - 优化首屏加载速度
- **聊天对话页面** - 内置交互式聊天界面，支持流式输出和历史记录，修复时间戳显示问题

### 🔧 智能管理

- **OpenTelemetry 集成** - 分布式追踪和监控
- **健康监控** - 手动检查模式，节省 API 调用
- **自动故障转移** - 优先级/随机回退机制
- **熔断器模式** - 快速失败防止级联故障
- **并行测试** - 使用 pytest-xdist 加速测试执行（3-4倍提速）

### 📊 运营监控

- **性能统计** - 请求日志、Token 使用追踪
- **压力测试** - 内置 10k QPS 压力测试脚本
- **实时日志** - 彩色输出，错误追踪
- **可观测性配置** - 请求采样率、慢请求警告阈值

### 💬 对话管理

- **历史对话记录** - SQLite 数据库存储对话历史
- **多对话支持** - 创建、查看、删除多个对话
- **Token 用量统计** - 实时追踪输入/输出 Token
- **自动标题生成** - 提取首条消息自动创建对话标题
- **智能时间戳** - 修复 "Invalid Date" 问题，支持多种时间格式解析

### 🏢 多供应商支持

- **统一 API 接口** - 支持 Anthropic 兼容格式
- **直连模式** - 支持 Anthropic API 格式提供商（无需转换）
- **智能模型映射** - haiku→small, sonnet→middle, opus→big
- **供应商 Token 限制** - 支持配置 max_tokens_limit
- **细粒度权限控制** - 9 个权限点精确控制，支持按用户配置权限
- **多种认证方式** - 邮箱密码登录 + OAuth 社交登录（GitHub、Google、飞书、Microsoft、OIDC）

## 🎉 最新更新

### v1.6.0 (2025-11-29) - 国际化与用户体验全面提升

#### 🌐 完整国际化支持

- **新增 16 种语言**：中文、English、日本語、한국어、Français、Español、Deutsch、Русский、Português、Italiano、Nederlands、العربية、हिन्दी、ไทย、Tiếng Việt、Bahasa Indonesia
- **智能语言切换**：支持顶部导航栏一键切换语言，自动记忆用户偏好
- **全面本地化**：所有页面、表单、按钮、提示信息、Toast 消息完整翻译
- **API Keys 页面**：新增完整国际化支持，包括创建、编辑、删除、搜索等所有操作

#### 🐛 问题修复

- **修复聊天时间戳**：解决 "Invalid Date" 问题，支持多种时间格式（ISO 8601、SQLite 时间戳等）
- **Svelte 5 合规性**：全面升级到 Svelte 5 语法，使用 `$state()` 和 `$derived()` 等新特性
- **响应式状态管理**：修复 API Keys 页面新建后需要刷新才能显示的问题
- **代码质量提升**：通过 `pnpm run check` 和 `pnpm run lint` 所有检查

#### 📈 技术改进

- **模块化翻译系统**：集中管理的翻译键，易于维护和扩展
- **优雅降级处理**：时间解析失败时自动返回空字符串，不显示错误信息
- **性能优化**：响应式状态优化，减少不必要的重新渲染

## 🏃‍♂️ 快速开始

### 环境要求

- **Python 3.9+** (推荐 3.10+)
- **Node.js 18+** (推荐 20+)
- **npm/pnpm/yarn** (推荐 pnpm)
- **Docker & Docker Compose** (可选，用于容器化部署)

### 🚀 一键部署（推荐）

#### Docker Compose 方式

```bash
# 克隆项目
git clone https://github.com/MichaelHuang7119/cc-switch.git
cd cc-switch

# 启动所有服务（后端 + 前端）
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f frontend
docker-compose logs -f backend
```

服务启动后：

- **前端管理界面**: http://localhost:5173
- **API 文档**: http://localhost:8000/docs

#### 自定义前端端口

```bash
EXPOSE_PORT=5175 docker-compose up -d
```

#### 本地开发方式

**1. 启动后端服务**

```bash
cd backend
bash start.sh  # 如果需保持热重载，可指定为"开发模式"，即：bash start.sh --dev
```

**2. 启动前端服务（新终端）**

```bash
cd frontend
# bash 启动
bash start.sh  # 如果需保持热重载，可指定为"开发模式"，即：bash start.sh --dev
# npm/pnpm启动（可指定端口）
pnpm install  # or: npm install, 首次运行需要安装依赖
pnpm dev -- --port 5173  # or: npm dev -- --port 5173
```

### 🔑 首次登录

1. 访问前端管理界面：http://localhost:5173
2. 系统会自动跳转到登录页面
3. 使用默认管理员账号登录：
   - **邮箱**：`admin@example.com`
   - **密码**：`admin123`

> **重要**：首次登录后请立即修改密码！生产环境需要设置强密码。

### ⚙️ 配置必需环境变量

**生产环境请设置以下环境变量，以保证数据安全和支持更多的配置**：

```bash
# 必需 - JWT 密钥
export JWT_SECRET_KEY="your-strong-secret-key-here"

# 推荐 - 加密密钥（用于敏感数据加密）
export ENCRYPTION_KEY="your-fernet-encryption-key-here"

# 推荐 - 管理员密码（至少 12 字符）
export ADMIN_PASSWORD="your-secure-password"

# 性能优化 - 数据库连接池
export DB_POOL_SIZE=20
export DB_POOL_TIMEOUT=30.0

# 性能优化 - HTTP 连接池
export HTTP_MAX_KEEPALIVE_CONNECTIONS=100
export HTTP_MAX_CONNECTIONS=500
export HTTP_KEEPALIVE_EXPIRY=60

# 性能优化 - 缓存配置
export CACHE_TYPE=multi
export CACHE_MULTI_LEVEL=true
export REDIS_URL=redis://localhost:6379/0
export CACHE_MAX_SIZE=1000
export CACHE_DEFAULT_TTL=3600

# 可选 - 监控配置
export ENABLE_TELEMETRY=true
export OTLP_ENDPOINT=http://jaeger:4318
export SERVICE_VERSION=1.0.0
```

## 🔧 开发指南

### 环境搭建

**1. 克隆项目**

```bash
git clone https://github.com/MichaelHuang7119/cc-switch.git
cd cc-switch
```

**2. 后端开发环境**

```bash
cd backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -e .

# 设置环境变量
cp .env.example .env
# 编辑 .env 文件，配置必要的环境变量
```

**3. 前端开发环境**

```bash
cd frontend

# 安装 pnpm（如果未安装）
npm install -g pnpm

# 安装依赖
pnpm install

# 启动开发服务器
pnpm dev
```

### 代码规范

**后端 (Python)**
- 使用 `black` 格式化代码
- 使用 `isort` 排序导入
- 使用 `pylint` 进行静态分析
- 使用 `pytest` 进行单元测试

```bash
# 格式化代码
black .
isort .

# 运行测试
pytest

# 运行测试（并行）
pytest -n auto

# 代码覆盖率
pytest --cov=app --cov-report=html
```

**前端 (TypeScript/Svelte)**
- 使用 `eslint` 进行代码检查
- 使用 `prettier` 格式化代码
- 使用 `svelte-check` 进行类型检查
- 遵循 Svelte 5 最新语法规范

```bash
# 类型检查
pnpm run check

# 代码检查
pnpm run lint

# 修复代码风格
pnpm run lint -- --write

# 构建生产版本
pnpm run build

# 预览构建结果
pnpm run preview
```

### 项目结构说明

**请求流程**

```
客户端请求
  ↓
API 路由 (/routes/messages.py, /routes/*.py)
  ↓
消息服务 (message_service.py)
  ↓
转换器 (converters/)
  ↓
供应商处理器 (services/handlers/)
  ↓
供应商客户端 (infrastructure/clients/)
  ↓
后端 AI 供应商 (OpenAI/Anthropic 格式)
  ↓
响应转换
  ↓
客户端
```

**后端核心流程**

```
用户请求
  │
  ▼
┌──────────────────┐
│   API 路由层      │  ← 验证请求参数、JWT 认证
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│    服务层         │  ← 业务逻辑处理
│  - 消息服务       │
│  - 供应商服务     │
│  - 健康检查服务   │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│    转换层         │  ← Anthropic ↔ OpenAI 格式转换
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│   供应商 API      │  ← 实际调用后端 AI 服务
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│   响应转换        │  ← 转换响应格式
└──────┬───────────┘
       │
       ▼
    返回用户
```

**前端状态流**

```
用户操作
  │
  ▼
┌──────────────────┐
│   Svelte 组件     │  ← 触发事件
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│    Stores        │  ← 状态管理
│  - writable      │
│  - derived       │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│   Services       │  ← API 调用
│  - api.ts        │
│  - auth.ts       │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  后端 API        │  ← 数据持久化
└──────────────────┘
```

### 调试指南

**后端调试**

1. 启用调试日志
```bash
export LOG_LEVEL=DEBUG
```

2. 使用 PyCharm/VSCode 调试
```bash
# 在 VSCode 中设置断点，然后：
python -m debugpy --listen 5678 --wait-for-child -m uvicorn app.main:app --reload
```

3. 数据库调试
```bash
# 查看数据库内容
sqlite3 backend/data/app.db
.tables
SELECT * FROM users;
```

**前端调试**

1. 浏览器开发者工具
```javascript
// 在控制台中查看stores
import { get } from 'svelte/store';
import { authService } from '$services/auth';
console.log(get(authService));
```

2. Svelte DevTools
```bash
# 安装浏览器扩展
# https://github.com/sveltejs/svelte-devtools
```

3. 网络请求调试
```bash
# 启用详细日志
localStorage.setItem('debug', 'http');
```

### 添加新功能

**1. 添加新的 API 端点**

创建文件：`backend/app/api/example.py`

```python
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/example", tags=["example"])

@router.get("/")
async def get_example():
    return {"message": "Hello"}
```

在 `main.py` 中注册：
```python
from .api.example import router as example_router
app.include_router(example_router)
```

**2. 添加新的前端页面**

创建文件：`frontend/src/routes/example/+page.svelte`

```svelte
<script lang="ts">
  let message = "Hello";
</script>

<h1>{message}</h1>
```

**3. 添加新的数据库表**

在 `backend/app/database/core.py` 的 `init_database()` 方法中添加：

```python
await cursor.execute("""
    CREATE TABLE IF NOT EXISTS example (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
```

## 📦 部署

### Docker 部署（推荐）

**生产环境**

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

**自定义配置**

创建 `.env.prod` 文件：

```bash
# 生产环境配置
JWT_SECRET_KEY=your-production-secret-key
ENCRYPTION_KEY=your-encryption-key
ADMIN_PASSWORD=your-secure-password

# 数据库配置
DATABASE_PATH=/data/app.db

# 性能配置
DB_POOL_SIZE=50
HTTP_MAX_CONNECTIONS=1000

# 日志配置
LOG_LEVEL=INFO
```

然后启动：

```bash
docker-compose --env-file .env.prod up -d
```

### Kubernetes 部署

```bash
# 部署到 K8s
kubectl apply -f k8s/
```

### 手动部署

**1. 后端部署**

```bash
cd backend
source venv/bin/activate

# 生产环境安装
pip install -e . --prod

# 使用 gunicorn 启动
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

**2. 前端部署**

```bash
cd frontend
pnpm install
pnpm build

# 将 build/ 目录部署到 Nginx
cp -r build/* /var/www/html/
```

## 🤝 贡献指南

我们欢迎所有形式的贡献！

### 如何贡献

1. **Fork** 项目
2. 创建功能分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -am 'Add some feature'`
4. 推送分支：`git push origin feature/your-feature`
5. 提交 **Pull Request**

### 贡献规范

**代码风格**
- 后端：遵循 PEP 8 规范
- 前端：遵循项目 ESLint 配置
- 提交信息：使用约定式提交格式

```bash
# 示例提交信息
feat(api): add new endpoint for statistics
fix(frontend): resolve chat timestamp issue
docs(readme): update deployment guide
```

**提交类型**
- `feat`: 新功能
- `fix`: 错误修复
- `docs`: 文档更新
- `style`: 代码格式
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建过程或辅助工具

**Pull Request 要求**
- [ ] 代码通过所有测试
- [ ] 通过 ESLint/Prettier 检查
- [ ] 添加必要的单元测试
- [ ] 更新相关文档
- [ ] 使用英文撰写 PR 描述

### 报告问题

请使用 [GitHub Issues](https://github.com/michaelhuang7119/cc-switch/issues) 报告问题。

**Bug 报告模板**：

```markdown
## 🐛 Bug 描述
清晰简洁地描述这个bug。

## 🔄 复现步骤
1. 打开...
2. 点击...
3. 滚动到...
4. 看到错误

## ✅ 预期行为
清晰简洁地描述你预期会发生什么。

## 📸 截图
如果适用，添加截图。

## 🖥️ 环境信息
- OS: [e.g. Ubuntu 20.04]
- Browser: [e.g. Chrome 91]
- Python: [e.g. 3.11.0]
- Node.js: [e.g. 18.0.0]
```

### 功能请求

```markdown
## 🚀 功能描述
清晰简洁地描述你想要的功能。

## 💡 详细说明
详细描述这个功能的实现方案。

## 🎯 使用场景
描述这个功能的使用场景。
```

