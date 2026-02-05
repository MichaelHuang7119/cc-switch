# CC Switch

[![CI/CD Status](https://github.com/michaelhuang7119/cc-switch/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/michaelhuang7119/cc-switch/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-green.svg)](https://fastapi.tiangolo.com/)
[![Svelte 5](https://img.shields.io/badge/Svelte-5-orange.svg)](https://svelte.dev/)

一个基于 FastAPI 和 Svelte 5 的高性能 AI 模型代理服务，支持多供应商配置和管理。

## ✨ 项目简介

CC Switch 是一个企业级 API 代理服务，它实现了 Anthropic 兼容的 API 端点，并将请求转发到支持 OpenAI 兼容接口的后端供应商（如通义千问、ModelScope、AI Ping、Anthropic 等）。通过统一的 API 接口，您可以轻松切换不同的 AI 模型供应商，而无需修改客户端代码。

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
EXPOSE_PORT=5173 docker-compose up -d
```

#### 本地开发方式

**1. 启动后端服务**

```bash
cd backend
bash start.sh # 如果需保持热重载，可指定为 "开发模式"，即：bash start.sh --dev
# 或直接运行
python start_proxy.py
```

**2. 启动前端服务（新终端）**

```bash
cd frontend
# bash 启动
bash start.sh # 如果需保持热重载，可指定为 "开发模式"，即：bash start.sh --dev
# npm/pnpm启动（可指定端口）
pnpm install  # or: npm install, 首次运行需要安装依赖
pnpm dev -- --port 5173 # or: npm dev -- --port 5173
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

## 🏢 配置 AI 供应商

**启动前必须先配置供应商信息！**

#### 方式一：编辑配置文件（推荐）

编辑 `backend/provider.json` 文件：

```json
{
  "providers": [
    {
      "name": "qwen",
      "enabled": true,
      "priority": 1,
      "api_key": "${QWEN_API_KEY}",
      "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "timeout": 60,
      "max_retries": 1,
      "models": {
        "big": ["qwen-plus", "qwen-max"],
        "middle": ["qwen-turbo"],
        "small": ["qwen-plus"]
      }
    },
    {
      "name": "anthropic-direct",
      "enabled": true,
      "priority": 2,
      "api_key": "${ANTHROPIC_API_KEY}",
      "base_url": "https://api.anthropic.com",
      "api_format": "anthropic",
      "timeout": 60,
      "max_retries": 1,
      "models": {
        "big": ["claude-3-opus-20240229"],
        "middle": ["claude-3-sonnet-20240229"],
        "small": ["claude-3-haiku-20240307"]
      }
    }
  ],
  "fallback_strategy": "priority",
  "circuit_breaker": {
    "failure_threshold": 5,
    "recovery_timeout": 60
  }
}
```

#### 方式二：Web 界面配置

1. 启动服务后登录管理界面
2. 访问"供应商"页面
3. 点击"添加供应商"按钮
4. 填写供应商信息（名称、Base URL、API Key等）
5. 配置模型列表（大、中、小三个类别）
6. 保存配置

![Providers](images/Providers.png)

### 🔑 配置 Claude Code

1. **创建 API Key**：

**方式一：使用 cURL 通过后端接口创建**

> 创建 API Key 需要管理员权限，需先获取 JWT Token。

```bash
# 步骤 1：登录获取 JWT Token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin123"}'
```

返回示例：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "admin@example.com",
    "name": "Administrator",
    "is_admin": true
  }
}
```

```bash
# 步骤 2：创建 API Key
curl -X POST http://localhost:8000/api/api-keys \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <你的_JWT_token>" \
  -d '{"name": "my-api-key", "email": "admin@example.com"}'
```

返回示例：
```json
{
  "id": 1,
  "api_key": "sk-abc123...",  // 完整 API Key 仅在此刻返回，请妥善保管
  "key_prefix": "sk-abc1...",
  "name": "my-api-key",
  "email": "admin@example.com",
  "is_active": true
}
```

**方式二：通过前端界面创建**

- 登录管理界面
- 访问「API Key 管理」页面
- 点击「创建 API Key」
- 填写名称和邮箱（可选）
- 复制生成的 API Key（**注意：创建后无法再次查看完整 Key**）

2. **配置 Claude Code 环境变量**：

```bash
# 仅启动后端时（假设后端端口为 8000）
export ANTHROPIC_BASE_URL=http://localhost:8000

# 前后端同时启动时，也可直接通过前端代理访问（前端端口如 5173）
export ANTHROPIC_BASE_URL=http://localhost:5173

# API Key：开发模式下可设为任意值；生产模式下需使用创建的有效 Key
export ANTHROPIC_API_KEY="sk-xxxxxxxxxxxxx"

# Claude Code 模型配置：haiku（小模型）、sonnet（中模型）、opus（大模型）
# 分别对应 provider.json 中的 small、middle、big 三类模型
# 例如：
# export ANTHROPIC_MODEL="sonnet"
# export ANTHROPIC_SMALL_FAST_MODEL="haiku"
# export ANTHROPIC_DEFAULT_SONNET_MODEL="sonnet"
# export ANTHROPIC_DEFAULT_OPUS_MODEL="opus"
# export ANTHROPIC_DEFAULT_HAIKU_MODEL="haiku"
```

### 🔐 配置 OAuth 登录（可选）

系统支持多种 OAuth 提供商进行社交登录。配置相应的环境变量以启用：

```bash
# GitHub OAuth
export GITHUB_CLIENT_ID="your-github-client-id"
export GITHUB_CLIENT_SECRET="your-github-client-secret"

# Google OAuth
export GOOGLE_CLIENT_ID="your-google-client-id"
export GOOGLE_CLIENT_SECRET="your-google-client-secret"

# 飞书 OAuth (Lark)
export FEISHU_CLIENT_ID="your-feishu-client-id"
export FEISHU_CLIENT_SECRET="your-feishu-client-secret"

# Microsoft OAuth (Azure AD)
export MICROSOFT_CLIENT_ID="your-microsoft-client-id"
export MICROSOFT_CLIENT_SECRET="your-microsoft-client-secret"
export MICROSOFT_TENANT_ID="common"  # 或特定的租户 ID

# 通用 OIDC（支持 Logto、Keycloak、Authentik 等）
export OIDC_CLIENT_ID="your-oidc-client-id"
export OIDC_CLIENT_SECRET="your-oidc-client-secret"
export OIDC_AUTHORIZATION_URL="https://your-oidc-server/oauth/authorize"
export OIDC_TOKEN_URL="https://your-oidc-server/oauth/token"
```

配置完成后，登录页面将显示相应的 OAuth 登录按钮。

![Login](images/Login.png)

## 📚 API 使用示例

### 基础消息请求

```bash
# 可直接访问后端（http://localhost:8000/v1/messages）
# 或通过前端代理（http://localhost:5173/v1/messages）
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-xxxxxxxxxxxxx" \
  -d '{
    "model": "haiku",
    "messages": [{"role": "user", "content": "你好！"}],
    "max_tokens": 100
  }'
```

### 流式请求

```bash
# 可直接访问后端（http://localhost:8000/v1/messages）
# 或通过前端代理（http://localhost:5173/v1/messages）
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-xxxxxxxxxxxxx" \
  -d '{
    "model": "sonnet",
    "messages": [{"role": "user", "content": "给我讲个故事"}],
    "max_tokens": 200,
    "stream": true
  }'
```

### 工具调用（Function Calling）

```bash
# 可直接访问后端（http://localhost:8000/v1/messages）
# 或通过前端代理（http://localhost:5173/v1/messages）
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-xxxxxxxxxxxxx" \
  -d '{
    "model": "opus",
    "messages": [{"role": "user", "content": "北京今天天气怎么样？"}],
    "max_tokens": 200,
    "tools": [{
      "name": "get_weather",
      "description": "获取指定城市的天气信息",
      "input_schema": {
        "type": "object",
        "properties": {
          "location": {
            "type": "string",
            "description": "城市名称"
          }
        },
        "required": ["location"]
      }
    }]
  }'
```

### 多模态输入（图片）

```bash
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-xxxxxxxxxxxxx" \
  -d '{
    "model": "sonnet",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "text", "text": "这张图片里有什么？"},
        {
          "type": "image",
          "source": {
            "type": "url",
            "url": "https://example.com/image.jpg"
          }
        }
      ]
    }],
    "max_tokens": 200
  }'
```

### Token 计数

```bash
curl -X POST http://localhost:8000/v1/messages/count_tokens \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-xxxxxxxxxxxxx" \
  -d '{
    "model": "haiku",
    "messages": [{"role": "user", "content": "测试消息"}]
  }'
```

### 对话历史管理API

#### 获取对话列表

```bash
curl -X GET http://localhost:8000/api/conversations \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### 创建新对话

```bash
curl -X POST http://localhost:8000/api/conversations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "provider_name": "qwen",
    "api_format": "openai",
    "model": "qwen-plus",
    "first_message": "你好！"
  }'
```

#### 获取对话详情（包含消息历史）

```bash
curl -X GET http://localhost:8000/api/conversations/123 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### 更新对话标题

```bash
curl -X PUT http://localhost:8000/api/conversations/123 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "title": "新的对话标题"
  }'
```

#### 删除对话

```bash
curl -X DELETE http://localhost:8000/api/conversations/123 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## 🏗️ 部署指南

### 🐳 Docker Compose（开发/测试环境）

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### ☸️ Kubernetes（生产环境）

参考 [k8s/README.md](./k8s/README.md) 获取详细的 Kubernetes 部署指南。

```bash
# 应用所有配置
kubectl apply -f k8s/

# 查看部署状态
kubectl get pods -n anthropic-bridge
```

### 🧪 性能测试

```bash
# 安装依赖
pip install aiohttp

# 运行压力测试（目标 10k QPS）
python scripts/load_test.py --url http://localhost:5173 --qps 10000 --duration 60
```

### 🔄 CI/CD 流水线

项目配置了 GitHub Actions CI/CD 流水线，支持自动化测试、构建和可选推送：

```bash
# GitHub Actions 流水线包含以下阶段：
# 1. 测试阶段：运行后端和前端测试（并行执行）
# 2. 构建阶段：自动构建 Docker 镜像
# 3. 可选推送：如果设置了 DOCKERHUB_TOKEN secret，自动推送到 Docker Hub
#    - 无secrets：仅构建，不推送
#    - 有secrets：构建并推送到 michael7119/cc-switch-{backend,frontend}
```

**CI/CD 特性**：

- ✅ 支持并行测试执行（pytest-xdist）
- ✅ 可选推送模式（无需secrets也能完整运行CI/CD）
- ✅ 自动缓存构建优化
- ✅ 测试覆盖率报告

CI/CD 配置文件位于：`.github/workflows/ci-cd.yml`

### 📊 监控

#### OpenTelemetry

如果启用了 OpenTelemetry，可以通过以下方式查看追踪和指标：

1. **Jaeger**：查看分布式追踪
2. **Prometheus**：查看指标（需要配置 Prometheus exporter）

#### 健康检查

- 后端：`http://localhost:8000/health`
- 前端：`http://localhost:5173/`

## 🏛️ 项目架构

### 整体架构

```
客户端请求 → 代理服务器 → 供应商API
     ↑                          ↓
  前端管理界面 ← 统一接口 ← 响应处理
```

### 请求流程

1. 客户端向代理服务器发送请求（携带 API Key）
2. 代理服务器验证 API Key
3. 代理服务器根据配置选择供应商
4. 转发请求到目标供应商 API
5. 接收响应并返回给客户端
6. 前端管理界面实时监控健康状态

### 项目结构

```
cc-switch/
├── backend/                    # 后端服务（FastAPI）
│   ├── app/
│   │   ├── api/               # API 路由层（RESTful API）
│   │   │   ├── auth.py        # 认证授权（JWT、API Key）
│   │   │   ├── config.py      # 配置管理API
│   │   │   ├── conversations.py # 对话历史API
│   │   │   ├── health.py      # 健康监控API
│   │   │   ├── providers.py   # 供应商管理API
│   │   │   ├── stats.py       # 统计分析API
│   │   │   └── api_keys.py    # API Key管理API
│   │   ├── routes/            # Anthropic API 路由层
│   │   │   ├── messages.py    # Anthropic messages API（/v1/messages）
│   │   │   └── health.py      # 健康检查路由
│   │   ├── services/          # 业务逻辑层
│   │   │   ├── config_service.py      # 配置管理服务
│   │   │   ├── message_service.py     # 消息处理核心服务
│   │   │   ├── provider_service.py    # 供应商服务
│   │   │   └── health_service.py      # 健康检查服务
│   │   ├── database/          # 数据库访问层
│   │   │   ├── core.py              # 数据库核心
│   │   │   ├── api_keys.py          # API Key管理
│   │   │   ├── config_changes.py    # 配置变更记录
│   │   │   ├── conversations.py     # 对话历史管理
│   │   │   ├── encryption.py        # 数据加密
│   │   │   ├── health_history.py    # 健康历史
│   │   │   ├── request_logs.py      # 请求日志
│   │   │   ├── token_usage.py       # Token使用统计
│   │   │   └── users.py             # 用户管理
│   │   ├── converters/        # 格式转换器（Anthropic ↔ OpenAI）
│   │   │   ├── anthropic_to_openai.py   # Anthropic转OpenAI
│   │   │   ├── openai_to_anthropic.py   # OpenAI转Anthropic
│   │   │   └── streaming.py             # 流式格式转换
│   │   ├── infrastructure/    # 基础设施层
│   │   │   ├── anthropic_client.py  # Anthropic API 客户端
│   │   │   ├── cache.py             # 缓存系统
│   │   │   ├── circuit_breaker.py   # 熔断器
│   │   │   ├── client.py            # HTTP客户端
│   │   │   ├── retry.py             # 重试机制
│   │   │   └── telemetry.py         # OpenTelemetry追踪
│   │   ├── config/            # 配置管理
│   │   │   ├── __init__.py
│   │   │   ├── main.py              # 主配置（Pydantic）
│   │   │   └── hot_reload.py        # 热重载支持
│   │   ├── core/              # 核心模块
│   │   │   ├── model_manager.py     # 模型管理器
│   │   │   └── models.py            # 数据模型
│   │   ├── security/          # 安全模块
│   │   │   └── utils.py             # 安全工具
│   │   ├── utils/             # 工具类
│   │   │   ├── color_logger.py      # 彩色日志
│   │   │   ├── error_handler.py     # 错误处理
│   │   │   └── response.py          # 响应格式化
│   │   ├── __init__.py
│   │   ├── auth.py            # 认证授权
│   │   ├── constants.py       # 常量定义
│   │   ├── lifecycle.py       # 应用生命周期
│   │   └── main.py            # FastAPI主应用
│   ├── provider.json          # 供应商配置
│   ├── provider.test.json     # 测试用供应商配置
│   ├── requirements.txt       # Python依赖（含pytest-xdist）
│   ├── start.sh               # 启动脚本
│   └── start_proxy.py         # 启动入口
│
├── frontend/                  # 前端管理界面（Svelte 5 + TypeScript）
│   ├── src/
│   │   ├── lib/               # 可复用组件和工具
│   │   │   ├── components/    # Svelte组件
│   │   │   │   ├── chat/              # 聊天组件
│   │   │   │   │   ├── ChatArea.svelte      # 聊天区域
│   │   │   │   │   ├── ConversationSidebar.svelte # 对话侧边栏
│   │   │   │   │   ├── MessageBubble.svelte   # 消息气泡
│   │   │   │   │   ├── MessageInput.svelte    # 消息输入
│   │   │   │   │   └── ModelSelector.svelte   # 模型选择器
│   │   │   │   ├── ErrorMessageModal.svelte   # 错误提示模态框
│   │   │   │   └── ProviderForm.svelte        # 供应商表单
│   │   │   └── services/      # API服务
│   │   │       └── stats.ts        # 统计分析服务
│   │   ├── routes/            # SvelteKit路由
│   │   │   ├── +layout.svelte     # 布局
│   │   │   ├── +page.svelte       # 首页
│   │   │   ├── chat/+page.svelte  # 聊天页面
│   │   │   ├── login/+page.svelte # 登录页面
│   │   │   ├── providers/+page.svelte # 供应商管理
│   │   │   └── stats/+page.svelte # 统计页面
│   │   ├── app.html           # 应用HTML模板
│   │   ├── hooks.server.js    # 服务器钩子
│   │   └── service-worker.js  # PWA服务
│   ├── static/                # 静态资源
│   ├── package.json           # Node依赖
│   ├── pnpm-lock.yaml         # pnpm锁文件
│   ├── svelte.config.js       # Svelte配置
│   ├── vite.config.ts         # Vite配置
│   ├── tsconfig.json          # TypeScript配置
│   ├── nginx.conf             # Nginx配置
│   └── Dockerfile             # Docker配置
│
├── k8s/                       # Kubernetes部署配置
│   ├── backend-deployment.yaml
│   ├── frontend-deployment.yaml
│   ├── ingress.yaml
│   ├── namespace.yaml
│   ├── pvc.yaml
│   ├── redis-deployment.yaml
│   ├── secrets.yaml.example
│   └── README.md
│
├── tests/                     # 测试套件（并行执行）
│   ├── conftest.py            # pytest配置
│   ├── test_assistant_tool_use.py  # 工具调用测试
│   ├── test_converter.py           # 转换器测试
│   ├── test_count_tokens.py        # Token计数测试
│   ├── test_messages.py            # 消息API测试
│   ├── test_performance.py         # 性能测试
│   ├── test_streaming_format.py    # 流式格式测试
│   └── test_tool_use_format.py     # 工具使用格式测试
│
├── .github/                   # GitHub配置
│   └── workflows/
│       └── ci-cd.yml          # CI/CD流水线（Docker Hub可选推送）
│
├── docker-compose.yml         # Docker Compose配置
├── pytest.ini                # pytest配置（含-n auto）
├── requirements.txt           # 根目录依赖（通常为空）
└── README.md                 # 项目文档
```

## 🛠️ 技术栈

### 后端

- **FastAPI** - 现代、快速的 Web 框架
- **aiosqlite** - 异步数据库操作 + 连接池（支持 300+ 并发）
- **httpx** - HTTP 客户端（连接池优化，支持 10k QPS）
- **Pydantic** - 数据验证和设置管理（v2.x + ConfigDict）
- **OpenTelemetry** - 分布式追踪和监控（Jaeger + Prometheus）
- **pytest** - 测试框架（覆盖率报告）
- **SQLAlchemy** - SQL 工具包（future + ORM）
- **Pillow** - 图像处理（图片上传支持）
- **pypng** - PNG 图像处理

### 前端

- **Svelte 5** - 新一代前端框架（全新的响应式系统）
- **SvelteKit** - Svelte 应用框架（SSR + File-system Routing）
- **TypeScript** - 类型安全的 JavaScript
- **Vite** - 快速的前端构建工具（HMR + Tree-shaking + 代码分割）
- **PWA** - 离线支持和应用安装（Service Worker + App Manifest）
- **Sass/Less** - CSS 预处理器（样式系统）

### 基础设施

- **Docker** - 容器化平台（多阶段构建优化）
- **Kubernetes** - 生产环境部署（PVC + Ingress）
- **Redis** - 缓存服务（L2 缓存层 + Session 存储）
- **Nginx** - 反向代理和负载均衡（超时配置 + 缓存）
- **Nginx-proxy** - 跨域代理（前端请求转发）

### Token 限制配置

#### max_tokens 限制规则

系统支持配置每个供应商的 `max_tokens` 限制：

- **全局默认限制**：30000（Anthropic 的默认限制）
- **供应商级别限制**：在 `provider.json` 中为每个供应商配置 `max_tokens_limit`
- **动态限制**：优先使用供应商级别的限制（如果配置了，即使是10万，系统会遵从；如果未配置，则使用30万）

**配置文件示例**：

```json
{
  "providers": [
    {
      "name": "qwen",
      "max_tokens_limit": 32768,
      "models": {
        "big": ["qwen-plus"],
        "middle": ["qwen-turbo"],
        "small": ["qwen-plus"]
      }
    }
  ]
}
```

**限制层级**（优先级从高到低）：

1. 供应商配置中的 `max_tokens_limit`
2. 默认限制：`300000`（30万）

服务器端会根据该限制对请求的 `max_tokens` 进行验证：

```python
@field_validator("max_tokens")
def validate_max_tokens(cls, v):
    if v <= 0:
        raise ValueError("max_tokens must be positive")
    if v > 1000000:  # 系统绝对最大限制
        raise ValueError("max_tokens too large")
    return v
```

## 🔧 环境变量配置

### 必需变量

| 变量名           | 说明           | 默认值              | 备注                 |
| ---------------- | -------------- | ------------------- | -------------------- |
| `JWT_SECRET_KEY` | JWT Token 密钥 | -                   | 生产环境**必须**设置 |
| `ENCRYPTION_KEY` | 数据加密密钥   | -                   | 推荐设置             |
| `ADMIN_PASSWORD` | 管理员密码     | `admin123`          | 建议设置强密码       |
| `ADMIN_EMAIL`    | 管理员邮箱     | `admin@example.com` | -                    |

### 性能优化变量

| 变量名                           | 说明               | 默认值                     |
| -------------------------------- | ------------------ | -------------------------- |
| `DB_POOL_SIZE`                   | 数据库连接池大小   | `10`                       |
| `DB_POOL_TIMEOUT`                | 连接池超时时间     | `30.0`                     |
| `HTTP_MAX_KEEPALIVE_CONNECTIONS` | Keepalive 连接数   | `50`                       |
| `HTTP_MAX_CONNECTIONS`           | 最大连接数         | `200`                      |
| `HTTP_KEEPALIVE_EXPIRY`          | Keepalive 过期时间 | `60`                       |
| `CACHE_TYPE`                     | 缓存类型           | `memory`                   |
| `CACHE_MULTI_LEVEL`              | 启用多级缓存       | `false`                    |
| `CACHE_MAX_SIZE`                 | 内存缓存最大条目数 | `1000`                     |
| `CACHE_DEFAULT_TTL`              | 默认 TTL           | `3600`                     |
| `REDIS_URL`                      | Redis 连接 URL     | `redis://localhost:6379/0` |

### 监控配置

| 变量名             | 说明               | 默认值  |
| ------------------ | ------------------ | ------- |
| `ENABLE_TELEMETRY` | 启用 OpenTelemetry | `false` |
| `OTLP_ENDPOINT`    | OTLP 导出端点      | -       |
| `SERVICE_VERSION`  | 服务版本号         | `1.0.0` |

## 🧪 测试

### 并行测试执行

项目使用 `pytest-xdist` 实现并行测试，大幅提升测试执行速度：

```bash
# 并行运行所有测试（自动检测CPU核心数）
pytest tests/ -n auto

# 手动指定并行进程数
pytest tests/ -n 4

# 运行特定测试文件（并行）
pytest tests/test_messages.py -n auto
pytest tests/test_converter.py -n auto
pytest tests/test_assistant_tool_use.py -n auto
pytest tests/test_count_tokens.py -n auto
pytest tests/test_performance.py -n auto
pytest tests/test_tool_use_format.py -n auto

# 运行测试并显示详细输出
pytest tests/ -n auto -v

# 运行测试并显示覆盖率（并行执行）
pytest tests/ -n auto --cov=app --cov-report=term-missing

# 性能压力测试
python scripts/load_test.py --url http://localhost:5175 --qps 10000 --duration 60
```

### 性能提升

- **之前（串行）**：39个测试 ≈ 219秒（3分39秒）
- **之后（并行）**：39个测试 ≈ 60-90秒（2.5-3.5倍提速）

### 测试文件说明

- **test_messages.py** - 消息处理和 API 端点测试
- **test_converter.py** - 格式转换器测试
- **test_assistant_tool_use.py** - 工具调用功能测试
- **test_count_tokens.py** - Token 计数功能测试
- **test_performance.py** - 性能和并发测试
- **test_streaming_format.py** - 流式输出格式测试
- **test_tool_use_format.py** - 工具调用格式测试

**测试配置**：

- 配置文件：`pytest.ini`（已配置 `-n auto`）
- 测试依赖：`pytest-xdist==3.6.0`（已添加到 requirements.txt）

## ❓ 常见问题

### Q: 如何切换界面语言？

A: 点击顶部导航栏的语言切换按钮（显示当前语言简称，如 "ZH"、"EN" 等），即可在 16 种语言之间切换。系统会自动记忆您的语言偏好，下次访问时自动应用。

### Q: 新增的 API Key 为什么需要刷新页面才能看到？

A: v1.6.0 已修复此问题。新建 API Key 后会立即显示在列表中，无需手动刷新页面。如果遇到其他页面需要刷新才能显示数据的问题，请尝试清除浏览器缓存或联系技术支持。

### Q: 聊天页面的时间显示为 "Invalid Date" 怎么办？

A: v1.6.0 已修复此问题。现在系统支持多种时间格式（ISO 8601、SQLite 时间戳、YYYY-MM-DD HH:MM:SS 等），会自动智能解析。如果仍有问题，可能是数据源的时间戳格式异常。

### Q: 如何添加新的 AI 供应商？

A: 登录管理界面，访问"供应商"页面，点击"添加供应商"按钮，填写供应商信息即可。或者手动编辑 `backend/provider.json` 文件。

### Q: 如何实现故障转移？

A: 系统根据 `priority` 字段选择供应商，优先级越高（数字越小）越优先。当高优先级供应商不可用时，自动切换到下一个可用供应商。

### Q: 如何监控供应商健康状态？

A: 登录管理界面，访问"健康监控"页面，点击"刷新状态"按钮进行手动检查。系统会显示总体状态（健康、部分健康、不健康、未检查）和每个供应商的详细信息。健康检查仅在手动点击时进行，最大化节省 API 调用和 Token 消耗。

### Q: 如何使用聊天功能？

A: 登录管理界面，点击顶部导航栏的"聊天"菜单，进入聊天页面。在聊天页面你可以：

1. 从下拉菜单选择供应商、API格式和具体模型
2. 在输入框输入消息，按 Enter 发送
3. 查看实时流式输出
4. 保存对话历史到数据库
5. 在左侧边栏查看、加载或删除历史对话

聊天功能支持完整的对话历史管理，包括自动标题生成、Token用量统计等。

### Q: 如何创建 API Key？

A: 登录管理界面，访问"API Key 管理"页面，点击"创建 API Key"按钮，填写名称和邮箱（可选），保存后复制生成的 API Key。**注意：创建后无法再次查看完整 Key，请妥善保管。**

### Q: 忘记管理员密码怎么办？

A: 如果忘记了管理员密码，可以：

1. 删除数据库文件 `backend/data/app.db`
2. 重启后端服务，系统会重新创建默认管理员账号
3. 使用默认账号登录后立即修改密码

### Q: API Key 泄露了怎么办？

A: 登录管理界面，访问"API Key 管理"页面，找到对应的 API Key，点击"禁用"或"删除"按钮。建议定期轮换 API Key 以提高安全性。

### Q: max_tokens 限制如何工作？

A: 系统支持动态 max_tokens 限制，采用层级策略：

1. **供应商级别限制**：在 `provider.json` 中为每个供应商配置 `max_tokens_limit`
2. **系统硬性限制**：`1000000`（100万）

**优先级从高到低**：

- 供应商配置中的 `max_tokens_limit`
- `MessagesRequest` 验证器的 `max_tokens` 默认最大值（已从 10万 提升至 100万）

**示例配置**：

```json
{
  "name": "moonshot", // 月之暗面
  "max_tokens_limit": 64000 // 月之暗面支持较长输出
}
```

**注意**：

- Claude 3 系列：`max_tokens_to_sample` 在服务端转换后已过时
- 转换为 OpenAI 格式后，直接使用 `max_tokens` 参数
- 后端已移除旧的转换映射逻辑，避免 Token 限制误用

### Q: 生产环境如何优化性能？

A: 请参考 [DEPLOYMENT.md](./DEPLOYMENT.md) 中的生产环境配置建议，包括：

- 设置必需的 `JWT_SECRET_KEY` 和 `ENCRYPTION_KEY`
- 配置数据库和 HTTP 连接池
- 启用多级缓存
- 配置 OpenTelemetry 监控

## 🔒 安全注意事项

1. **生产环境必须设置**：
   - `JWT_SECRET_KEY` - 强随机密钥
   - `ENCRYPTION_KEY` - 加密密钥（用于敏感数据）
   - `ADMIN_PASSWORD` - 至少 12 字符的强密码

2. **API 密钥安全**：建议使用环境变量存储 API 密钥，不要将密钥直接写入配置文件

3. **HTTPS 配置**：生产环境请配置 TLS/SSL 证书

4. **访问控制**：使用防火墙或 Ingress 规则限制访问

5. **密钥管理**：使用专业的密钥管理服务（如 Kubernetes Secrets、HashiCorp Vault）

## 📁 配置文件说明

### 环境变量配置

**主要配置文件**：

- **`.env.example`** - Docker Compose 环境变量示例

  ```bash
  # 前端暴露端口（映射到宿主机端口）
  EXPOSE_PORT=5173
  ```

- **`backend/.env`** - 后端环境变量配置（需手动创建）

### 供应商配置示例

**`backend/provider.json.example`** - 供应商配置模板：

```json
{
  "providers": [
    {
      "name": "example-provider",
      "enabled": false,
      "priority": 1,
      "api_key": "your-api-key-here",
      "base_url": "https://api.example.com/v1",
      "timeout": 180,
      "max_retries": 2,
      "custom_headers": {},
      "models": {
        "big": ["claude-opus"],
        "middle": ["claude-sonnet"],
        "small": ["claude-haiku"]
      },
      "api_format": "openai",
      "max_tokens_limit": 32768
    }
  ],
  "fallback_strategy": "priority"
}
```

### 配置文件说明

| 配置文件                        | 说明                | 用途                    |
| ------------------------------- | ------------------- | ----------------------- |
| `.env.example`                  | Docker 环境变量示例 | Docker Compose 部署配置 |
| `backend/provider.json`         | 供应商配置文件      | 主配置文件（需配置）    |
| `backend/provider.json.example` | 供应商配置模板      | 配置参考                |
| `pytest.ini`                    | 测试配置            | pytest 测试框架配置     |
| `docker-compose.yml`            | Docker Compose 配置 | 容器编排配置            |
| `.github/workflows/ci-cd.yml`   | CI/CD 配置          | 自动化构建部署          |

## 🛠️ 工具脚本和依赖管理

### 性能测试脚本

**`scripts/load_test.py`** - 高性能负载测试工具：

```bash
# 基本用法
python scripts/load_test.py --url http://localhost:5173 --qps 10000 --duration 60

# 高级参数
python scripts/load_test.py \
  --url http://localhost:5173 \
  --qps 10000 \
  --duration 60 \
  --concurrency 100 \
  --api-key sk-test-key \
  --model haiku
```

**脚本特性**：

- 异步并发请求
- 可配置 QPS 和持续时间
- 详细的性能统计（响应时间、成功率、QPS 等）
- 支持自定义 API Key 和模型

### 测试验证脚本

**`scripts/test_all.py`** - 全面的测试验证工具：

```bash
# 验证所有测试文件语法和功能
python scripts/test_all.py
```

**验证内容**：

- 检查所有测试文件的Python语法
- 验证流式格式测试功能
- 测试文件完整性检查
- 提供详细的测试报告

**测试文件列表**：

- `test_assistant_tool_use.py` - 工具调用功能测试
- `test_converter.py` - 格式转换器测试
- `test_count_tokens.py` - Token计数功能测试
- `test_messages.py` - 消息处理和API端点测试
- `test_performance.py` - 性能和并发测试
- `test_streaming_format.py` - 流式输出格式验证测试 ✅
- `test_tool_use_format.py` - 工具调用格式测试

### 启动脚本

**三种启动方式**：

1. **项目根目录启动脚本**：

```bash
# 一键启动（启动后端和前端）
bash start.sh
```

2. **后端启动脚本**：

```bash
# 使用默认配置启动后端
bash backend/start.sh

# 或直接运行 Python 脚本
python backend/start_proxy.py
```

3. **前端启动脚本**：

```bash
# 启动前端开发服务器
bash frontend/start.sh

# 或直接运行
pnpm --prefix frontend dev
```

### 测试验证和CI/CD

项目包含完整的测试验证脚本和优化的CI/CD配置：

```bash
# 验证测试配置
python scripts/test_validation.py

# 本地运行测试验证
cd backend && cp ../pytest.ini ./ && cp -r ../tests ./ && PYTHONPATH=. pytest tests/ --cov=app
```

**CI/CD 优化**：

- 修复了pytest路径问题
- 优化了覆盖率报告生成
- 解决了"collected 0 items"错误
- 配置了正确的Python模块路径

### 依赖管理

**`backend/requirements.txt`** - Python 依赖包：

```bash
cd backend
pip install -r requirements.txt
```

## 📄 许可证

MIT License - 详情请查看 [LICENSE](LICENSE) 文件

```
MIT License

Copyright (c) 2025 CC Switch

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 🔗 相关链接

- **项目主页**：<https://github.com/michaelhuang7119/cc-switch>
- **问题反馈**：<https://github.com/michaelhuang7119/cc-switch/issues>
- **功能建议**：<https://github.com/michaelhuang7119/cc-switch/discussions>
- **API 文档**：<http://localhost:8000/docs>
- **Docker Hub 镜像**：
  - Backend: <https://hub.docker.com/r/michael7119/cc-switch-backend>
  - Frontend: <https://hub.docker.com/r/michael7119/cc-switch-frontend>
- **Kubernetes 部署**：请查看 [k8s/README.md](./k8s/README.md)

## 🗺️ 路线图

### v1.6.0 (已完成 - 2025-01-29) ✅

- [x] **多语言支持** - 完整支持16种语言，智能语言切换
- [x] **时间戳修复** - 解决 "Invalid Date" 问题
- [x] **Svelte 5 升级** - 全面使用新响应式系统

### v1.7.0 (规划中)

- [ ] **插件系统** - 支持自定义插件扩展功能
- [ ] **指标仪表板** - 详细的性能和使用指标
- [ ] **告警系统** - 支持邮件/Webhook 告警

### v1.5.0 (规划中)

- [ ] **集群部署** - 支持多节点部署
- [ ] **负载均衡** - 内置负载均衡算法
- [ ] **灰度发布** - 支持 A/B 测试
- [ ] **自动扩缩容** - 基于负载的动态扩缩容

### v2.0.0 (长期规划)

- [ ] **微服务架构** - 完全微服务化
- [ ] **实时协作** - 多用户实时编辑配置
- [ ] **AI 模型市场** - 内置模型市场
- [ ] **GraphQL 支持** - 支持 GraphQL 查询

## 🏆 致谢

感谢以下开源项目：

- [FastAPI](https://fastapi.tiangolo.com/) - 现代化 Python Web 框架
- [Svelte](https://svelte.dev/) - 新一代前端框架
- [Docker](https://www.docker.com/) - 容器化平台
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python SQL 工具包
- [Pydantic](https://pydantic-docs.helpmanual.io/) - 数据验证库
- [Nginx](https://www.nginx.com/) - 高性能 Web 服务器
- [OpenTelemetry](https://opentelemetry.io/) - 可观测性标准
- [Kubernetes](https://kubernetes.io/) - 容器编排平台

特别感谢所有贡献者和用户！

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个 Star 支持一下！**

Made with ❤️ by CC Switch Team

</div>
