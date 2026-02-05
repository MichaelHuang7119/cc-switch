# CC Switch

[![CI/CD Status](https://github.com/michaelhuang7119/cc-switch/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/michaelhuang7119/cc-switch/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-green.svg)](https://fastapi.tiangolo.com/)
[![Svelte 5](https://img.shields.io/badge/Svelte-5-orange.svg)](https://svelte.dev/)

A high-performance AI model proxy service based on FastAPI and Svelte 5, supporting multi-provider configuration and management.

## ✨ Project Introduction

CC Switch is an enterprise-grade API proxy service that implements Anthropic-compatible API endpoints and forwards requests to backend providers supporting OpenAI-compatible interfaces (such as Qwen, ModelScope, AI Ping, Anthropic, etc.). Through a unified API interface, you can easily switch between different AI model providers without modifying client code.

## 🏗️ Project Architecture

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Claude Code                           │
│                   (Client / CLI Tool)                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              CC Switch                         │
├─────────────────────┬───────────────────────────────────────┤
│    Frontend         │            Backend                    │
│                     │                                       │
│  ┌───────────────┐  │  ┌─────────────────────────────────┐  │
│  │  Svelte 5     │  │  │     FastAPI + Uvicorn          │  │
│  │  TypeScript   │  │  │                                 │  │
│  │  PWA          │  │  │  ┌───────────────────────────┐  │  │
│  │               │  │  │  │   API Routes              │  │  │
│  │  - Chat UI    │  │  │  │  - /v1/messages           │  │  │
│  │  - Dashboard  │  │  │  │  - /api/providers         │  │  │
│  │  - Health     │  │  │  │  - /api/health            │  │  │
│  │  - Settings   │  │  │  │  - /api/stats             │  │  │
│  └───────────────┘  │  │  └───────────────────────────┘  │  │
│                     │  │                                 │  │
│  ┌───────────────┐  │  │  ┌───────────────────────────┐  │  │
│  │   WebSocket   │  │  │  │    Service Layer         │  │  │
│  │   Real-time   │  │  │  │                           │  │  │
│  └───────────────┘  │  │  │  - MessageService         │  │  │
│                     │  │  │  - ProviderService        │  │  │
└─────────────────────┴──┴──┴───────────────────────────┴──┘
                        │                                   │
                        ▼                                   ▼
              ┌─────────────────┐                  ┌──────────────────┐
              │   Browser       │                  │    Data Layer    │
              │   Storage       │                  │                  │
              │   (localStorage)│                  │  ┌────────────┐ │
              └─────────────────┘                  │  │ SQLite DB  │ │
                                                 │  └────────────┘ │
                                                 │                  │
                                                 │  ┌────────────┐ │
                                                 │  │ Connection │ │
                                                 │  │  Pool      │ │
                                                 │  └────────────┘ │
                                                 └──────────────────┘
```

### Backend Architecture (Backend)

Backend is based on **FastAPI** framework, using a layered architecture design:

#### Directory Structure

```
backend/app/
├── routes/                  # API routes
│   ├── messages.py          # Message API (Anthropic compatible)
│   ├── health.py            # Health check routes
│   ├── auth.py              # Authentication routes
│   ├── oauth.py             # OAuth routes
│   └── ...
├── services/                # Business logic layer
│   ├── message_service.py   # Message handling
│   ├── provider_service.py  # Provider management
│   ├── auth_service.py      # Authentication service
│   ├── health_service.py    # Health monitoring
│   ├── token_counter.py     # Token counting
│   └── ...
├── converters/              # Format converters
│   ├── anthropic_to_openai.py
│   ├── openai_to_anthropic.py
│   └── streaming_format.py
├── infrastructure/          # Infrastructure services
│   ├── cache.py             # In-memory/Redis cache
│   └── telemetry.py         # OpenTelemetry integration
├── database/                # Data access layer (async SQLite)
│   ├── core.py              # Database connection & schema
│   ├── users.py             # User management
│   ├── api_keys.py          # API key storage
│   ├── conversations.py     # Chat conversations & messages
│   ├── request_logs.py      # Request logging
│   ├── token_usage.py       # Token usage tracking
│   ├── health_history.py    # Health history
│   ├── config_changes.py    # Config change history
│   ├── oauth_accounts.py    # OAuth account associations
│   └── encryption.py        # Encryption utilities
├── utils/                   # Utility functions
│   ├── token_extractor.py   # Unified token extraction (supports OpenAI/Anthropic)
│   ├── security_utils.py    # Encryption, validation, API key masking
│   ├── color_logger.py      # Colored logging
│   ├── error_handler.py     # Error response formatting
│   └── response.py          # Response utilities
└── encryption_key.py        # Encryption key management
```

#### Core Components

**1. API Layer (`/api/`)**
- Expose RESTful API endpoints
- Handle HTTP requests/responses
- Validate request parameters
- JWT authentication

**2. Service Layer (`/services/`)**
- Business logic processing
- Provider request forwarding
- Failover handling
- Concurrency control

**3. Data Layer (`/database/`)**
- SQLite database + connection pool
- Async data access
- Encrypted data storage
- Request logging

**4. Conversion Layer (`/converters/`)**
- Anthropic ↔ OpenAI format conversion
- Streaming response handling
- Tool calling format conversion

### Frontend Architecture (Frontend)

Frontend is based on **Svelte 5** framework, using modern responsive design:

#### Directory Structure

```
frontend/src/
├── lib/
│   ├── components/            # Reusable Svelte components
│   │   ├── chat/              # Chat-related components (ChatArea, MessageBubble, etc.)
│   │   ├── layout/            # Layout components (Header, MobileNav)
│   │   ├── providers/         # Provider management components
│   │   ├── settings/          # Settings components
│   │   ├── ui/                # Base UI components (Button, Input, Card, etc.)
│   │   ├── i18n/              # Internationalization component (Translate)
│   │   ├── ErrorMessageModal.svelte
│   │   ├── Pagination.svelte
│   │   ├── ProviderForm.svelte
│   │   ├── SettingsModal.svelte
│   │   ├── WelcomeModal.svelte
│   │   └── OAuthIcon.svelte
│   ├── services/              # API client services
│   │   ├── api.ts             # Main API client
│   │   ├── chatService.ts     # Chat service
│   │   ├── auth.ts            # Auth service
│   │   ├── permissions.ts     # Permission management service
│   │   ├── oauthProviders.ts  # OAuth provider configuration
│   │   ├── apiKeys.ts         # API Key service
│   │   ├── apiKeyStorage.ts   # Secure API Key storage
│   │   ├── providers.ts       # Provider service
│   │   ├── health.ts          # Health monitoring service
│   │   ├── stats.ts           # Statistics service
│   │   ├── config.ts          # Config service
│   │   └── preferences.ts     # User preferences service
│   ├── stores/                # Svelte stores (Svelte 5 $state)
│   │   ├── auth.svelte.ts     # Auth state
│   │   ├── chatSession.ts     # Chat session state
│   │   ├── providers.ts       # Provider state
│   │   ├── health.ts          # Health state
│   │   ├── language.ts        # Internationalization state
│   │   ├── theme.ts           # Theme state
│   │   ├── toast.ts           # Toast message state
│   │   └── config.ts          # Config state
│   ├── types/                 # TypeScript type definitions
│   │   ├── permission.ts      # Permission types
│   │   ├── apiKey.ts          # API Key types
│   │   ├── provider.ts        # Provider types
│   │   ├── health.ts          # Health types
│   │   ├── config.ts          # Config types
│   │   └── language.ts        # Language types
│   ├── config/                # Configuration files
│   │   └── keyboardShortcuts.ts  # Keyboard shortcuts
│   ├── utils/                 # Utility functions
│   │   ├── gesture.ts         # Gesture detection
│   │   └── session.ts         # Session management
│   └── i18n/                  # Internationalization resources (16 languages)
├── routes/                    # SvelteKit pages
│   ├── +layout.svelte         # Root layout (auth & permission checks)
│   ├── +page.svelte           # Home page
│   ├── login/                 # Login page (email + OAuth)
│   │   └── +page.ts
│   ├── chat/                  # Chat page
│   ├── providers/             # Provider management
│   ├── api-keys/              # API Key management
│   ├── health/                # Health monitoring
│   ├── stats/                 # Usage statistics
│   ├── config/                # System configuration
│   ├── admin/
│   │   └── users/             # User management
│   │       ├── +page.svelte   # User list
│   │       └── [id]/          # User details & permission config
│   └── oauth/
│       └── [provider]/        # OAuth callback handling
│           └── callback/      # OAuth callback page
└── app.html                   # HTML template
```

#### Core Features

**1. Reactive State Management**
- Svelte 5 native `$state()` and `$derived()`
- Composable state management (similar to React hooks)
- Fine-grained reactive updates

**2. Service Layer Architecture**
- Unified API client (`api.ts`)
- Separation of concerns: authentication, chat, configuration, etc.
- Error handling and retry mechanisms

**3. State Management**
- Svelte Store lightweight state management
- Type-safe TypeScript definitions
- Persistent storage (localStorage)

**4. Internationalization (i18n)**
- 16 languages supported
- JSON format translation files
- Automatic language detection and switching

### Database Design

Using SQLite database to store all data:

#### Core Table Structure

**1. Users Table (`users`)**
```sql
- id (PRIMARY KEY)
- email (UNIQUE)
- password_hash
- name
- language (user language preference)
- is_admin
- is_active
- created_at
- updated_at
- last_login_at
```

**2. API Keys Table (`api_keys`)**
```sql
- id (PRIMARY KEY)
- key_hash (UNIQUE)
- key_prefix
- encrypted_key (encrypted storage)
- name
- email
- user_id (FOREIGN KEY)
- is_active
- last_used_at
- created_at
- updated_at
```

**3. Conversations Table (`conversations`)**
```sql
- id (PRIMARY KEY)
- user_id (FOREIGN KEY)
- title
- provider_name
- api_format
- model
- created_at
- updated_at
```

**4. Messages Table (`conversation_messages`)**
```sql
- id (PRIMARY KEY)
- conversation_id (FOREIGN KEY)
- role (user/assistant/system)
- content
- provider_name
- model
- input_tokens
- output_tokens
- thinking (reasoning process)
- created_at
```

**5. Request Logs Table (`request_logs`)**
```sql
- id (PRIMARY KEY)
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

### API Design

#### Core Endpoints

**1. Message API (Anthropic Compatible)**
- `POST /v1/messages` - Send message
- `POST /v1/messages/stream` - Stream messages

**2. Provider Management**
- `GET /api/providers` - Get provider list
- `POST /api/providers` - Add provider
- `PUT /api/providers/{id}` - Update provider
- `DELETE /api/providers/{id}` - Delete provider

**3. Health Checks**
- `GET /health` - Basic health check
- `GET /api/health` - Detailed health information
- `POST /api/health/check` - Manual trigger check

**4. Statistics**
- `GET /api/stats/token-usage` - Token usage statistics
- `GET /api/stats/requests` - Request statistics
- `GET /api/stats/providers` - Provider statistics

**5. Conversation Management**
- `GET /api/conversations` - Get conversation list
- `POST /api/conversations` - Create conversation
- `GET /api/conversations/{id}` - Get conversation details
- `DELETE /api/conversations/{id}` - Delete conversation
- `GET /api/conversations/{id}/messages` - Get message list

## 🚀 Key Features

### 🔥 High-Performance Architecture

- **Async Database** - aiosqlite + connection pool, eliminates blocking, improves concurrency 10-100x
- **HTTP Connection Pool Optimization** - Supports 10k QPS, Keepalive connection optimization
- **Multi-level Cache Architecture** - L1 (memory) + L2 (Redis) cache, significantly improves response speed

### 🛡️ Enterprise-Grade Security

- **JWT Key Enforcement** - Production environment must configure, otherwise generate temporary key with warning
- **Encryption Key Management** - ENCRYPTION_KEY support, sensitive data encrypted storage
- **Strong Password Policy** - At least 12 characters, admin password check

### 🌍 Internationalization Support

- **16 Languages Support** - Chinese, English, 日本語, 한국어, Français, Español, Deutsch, Русский, Português, Italiano, Nederlands, العربية, हिन्दी, ไทย, Tiếng Việt, Bahasa Indonesia
- **Smart Language Switching** - Automatic browser language detection, supports manual switching
- **Complete UI Translation** - All pages, forms, buttons, prompt messages fully localized
- **Local Storage** - Intelligently remembers user language preferences

### 🌐 Modern Management Interface

- **Svelte 5 + TypeScript** - Modern frontend framework, new reactive system, type safety
- **PWA Support** - Offline access, install to home screen, background sync
- **Dark/Light Theme** - User experience optimization
- **Code Splitting** - Optimizes first screen loading speed
- **Chat Page** - Built-in interactive chat interface, supports streaming output and history, fixed timestamp display issues

### 🔧 Smart Management

- **OpenTelemetry Integration** - Distributed tracing and monitoring
- **Health Monitoring** - Manual check mode, saves API calls
- **Automatic Failover** - Priority/random fallback mechanism
- **Circuit Breaker Pattern** - Fast failure prevents cascade failures
- **Parallel Testing** - Use pytest-xdist to accelerate test execution (3-4x speedup)

### 📊 Operations Monitoring

- **Performance Statistics** - Request logs, Token usage tracking
- **Stress Testing** - Built-in 10k QPS stress test script
- **Real-time Logs** - Color output, error tracking
- **Observability Configuration** - Request sampling rate, slow request warning threshold

### 💬 Conversation Management

- **Chat History** - SQLite database stores conversation history
- **Multi-conversation Support** - Create, view, delete multiple conversations
- **Token Usage Statistics** - Real-time tracking of input/output tokens
- **Auto Title Generation** - Extract first message to automatically create conversation title
- **Smart Timestamps** - Fixed "Invalid Date" issue, supports multiple time format parsing

### 🏢 Multi-Provider Support

- **Unified API Interface** - Supports Anthropic compatible format
- **Direct Mode** - Supports Anthropic API format providers (no conversion needed)
- **Smart Model Mapping** - haiku→small, sonnet→middle, opus→big
- **Provider Token Limits** - Supports configuring max_tokens_limit
- **Fine-Grained Permission Control** - 9 permission points for precise access control, per-user permission configuration
- **Multiple Authentication Methods** - Email/password login + OAuth social login (GitHub, Google, Feishu, Microsoft, OIDC)

## 📝 Latest Updates

### v1.6.0 (2025-11-29) - Comprehensive internationalization and user experience improvements

#### 🌐 Complete Internationalization Support

- **16 Languages Added**: Chinese, English, 日本語, 한국어, Français, Español, Deutsch, Русский, Português, Italiano, Nederlands, العربية, हिन्दी, ไทย, Tiếng Việt, Bahasa Indonesia
- **Smart Language Switching**: One-click language switching in top navigation bar, automatically remembers user preferences
- **Full Localization**: All pages, forms, buttons, prompt messages, Toast notifications completely translated
- **API Keys Page**: Added complete internationalization support, including all operations like create, edit, delete, search, etc.

#### 🐛 Bug Fixes

- **Fixed Chat Timestamps**: Resolved "Invalid Date" issue, supports multiple time formats (ISO 8601, SQLite timestamps, etc.)
- **Svelte 5 Compliance**: Fully upgraded to Svelte 5 syntax, using `$state()` and `$derived()` features
- **Fixed API Keys Page**: Resolved issue where new items required page refresh to display
- **Code Quality Improvement**: Passed all checks via `pnpm run check` and `pnpm run lint`

#### 📈 Technical Improvements

- **Modular Translation System**: Centrally managed translation keys, easy to maintain and extend
- **Graceful Degradation Handling**: Returns empty string when time parsing fails, no error messages displayed
- **Performance Optimization**: Reactive state optimization, reduced unnecessary re-renders

## 🏃‍♂️ Quick Start

### Environment Requirements

- **Python 3.9+** (recommended 3.10+)
- **Node.js 18+** (recommended 20+)
- **npm/pnpm/yarn** (recommended pnpm)
- **Docker & Docker Compose** (optional, for containerized deployment)

### 🚀 One-Click Deployment (Recommended)

#### Docker Compose

```bash
# Clone the repository
git clone https://github.com/MichaelHuang7119/cc-switch.git
cd cc-switch

# Start all services (backend + frontend)
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f frontend
docker-compose logs -f backend
```

After starting the services:

- **Frontend Management Interface**: http://localhost:5173
- **API Documentation**: http://localhost:8000/docs

#### Custom Frontend Port

```bash
EXPOSE_PORT=5175 docker-compose up -d
```

#### Local Development

**1. Start Backend Service**

```bash
cd backend
bash start.sh  # With hot reload for development mode: bash start.sh --dev
# Or run directly
python start_proxy.py
```

**2. Start Frontend Service (New Terminal)**

```bash
cd frontend
pnpm install  # Install dependencies first time
pnpm dev
# Or specify port
pnpm dev -- --port 5173
```

### 🔑 First Login

1. Visit frontend management interface: http://localhost:5173
2. System will automatically redirect to login page
3. Use default admin credentials:
   - **Email**: `admin@example.com`
   - **Password**: `admin123`

> **Important**: Please change the password immediately after first login! Production environments require strong passwords.

### ⚙️ Required Environment Variables

**Production environment must set the following environment variables**:

```bash
# Required - JWT secret key
export JWT_SECRET_KEY="your-strong-secret-key-here"

# Recommended - Encryption key (for sensitive data encryption)
export ENCRYPTION_KEY="your-fernet-encryption-key-here"

# Recommended - Admin password (at least 12 characters)
export ADMIN_PASSWORD="your-secure-password"

# Performance optimization - database connection pool
export DB_POOL_SIZE=20
export DB_POOL_TIMEOUT=30.0

# Performance optimization - HTTP connection pool
export HTTP_MAX_KEEPALIVE_CONNECTIONS=100
export HTTP_MAX_CONNECTIONS=500
export HTTP_KEEPALIVE_EXPIRY=60

# Performance optimization - cache configuration
export CACHE_TYPE=multi
export CACHE_MULTI_LEVEL=true
export REDIS_URL=redis://localhost:6379/0
export CACHE_MAX_SIZE=1000
export CACHE_DEFAULT_TTL=3600

# Optional - monitoring configuration
export ENABLE_TELEMETRY=true
export OTLP_ENDPOINT=http://jaeger:4318
export SERVICE_VERSION=1.0.0
```

## 🏢 Configure AI Providers

**Must configure provider information before startup!**

#### Method 1: Via Environment Variables (Recommended)

```bash
# Set environment variables
export QWEN_API_KEY="your-qwen-api-key"
export MODELSCOPE_API_KEY="your-modelscope-api-key"
export AIPING_API_KEY="your-aiping-api-key"
export MOONSHOT_API_KEY="your-moonshot-api-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```

#### Method 2: Configuration File

Edit the `backend/provider.json` file:

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

#### Method 3: Web Interface Configuration

1. Start the service and login to management interface
2. Visit "Providers" page
3. Click "Add Provider" button
4. Fill in provider information (name, base URL, API key, etc.)
5. Configure model list (big, middle, small three categories)
6. Save configuration

## 🔑 Configure Claude Code

1. **Create API Key**:

**Method 1: Create via cURL using backend API**

> Creating an API Key requires admin privileges. You must obtain a JWT token first.

```bash
# Step 1: Login to get JWT token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin123"}'
```

Response example:
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
# Step 2: Create API Key
curl -X POST http://localhost:8000/api/api-keys \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your_JWT_token>" \
  -d '{"name": "my-api-key", "email": "admin@example.com"}'
```

Response example:
```json
{
  "id": 1,
  "api_key": "sk-abc123...",  // Full API Key is only shown now, please store it safely
  "key_prefix": "sk-abc1...",
  "name": "my-api-key",
  "email": "admin@example.com",
  "is_active": true
}
```

**Method 2: Create via frontend interface**

- Login to management interface
- Visit "API Key Management" page
- Click "Create API Key"
- Fill in name and email (optional)
- Copy the generated API Key (**Note: Cannot view the full key after creation**)

2. **Configure Claude Code Environment Variables**:

```bash
# Backend only (assuming backend port is 8000)
export ANTHROPIC_BASE_URL=http://localhost:8000

# When both frontend and backend are running, you can also access via frontend proxy (e.g., port 5173)
export ANTHROPIC_BASE_URL=http://localhost:5173

# API Key: in development mode, can be any value; in production, use the created valid key
export ANTHROPIC_API_KEY="sk-xxxxxxxxxxxxx"

# Claude Code model configuration: haiku (small), sonnet (middle), opus (big)
# These correspond to the small, middle, big model tiers in provider.json
# For example:
# export ANTHROPIC_MODEL="sonnet"
# export ANTHROPIC_SMALL_FAST_MODEL="haiku"
# export ANTHROPIC_DEFAULT_SONNET_MODEL="sonnet"
# export ANTHROPIC_DEFAULT_OPUS_MODEL="opus"
# export ANTHROPIC_DEFAULT_HAIKU_MODEL="haiku"
```

### 🔐 Configure OAuth Login (Optional)

The system supports multiple OAuth providers for social login. Configure the corresponding environment variables to enable:

```bash
# GitHub OAuth
export GITHUB_CLIENT_ID="your-github-client-id"
export GITHUB_CLIENT_SECRET="your-github-client-secret"

# Google OAuth
export GOOGLE_CLIENT_ID="your-google-client-id"
export GOOGLE_CLIENT_SECRET="your-google-client-secret"

# Feishu OAuth (Lark)
export FEISHU_CLIENT_ID="your-feishu-client-id"
export FEISHU_CLIENT_SECRET="your-feishu-client-secret"

# Microsoft OAuth (Azure AD)
export MICROSOFT_CLIENT_ID="your-microsoft-client-id"
export MICROSOFT_CLIENT_SECRET="your-microsoft-client-secret"
export MICROSOFT_TENANT_ID="common"  # or specific tenant ID

# Generic OIDC (supports Logto, Keycloak, Authentik, etc.)
export OIDC_CLIENT_ID="your-oidc-client-id"
export OIDC_CLIENT_SECRET="your-oidc-client-secret"
export OIDC_AUTHORIZATION_URL="https://your-oidc-server/oauth/authorize"
export OIDC_TOKEN_URL="https://your-oidc-server/oauth/token"
```

After configuration, the login page will display the corresponding OAuth login buttons.

![Login](images/Login.png)

## 📚 API Usage Examples

### Basic Message Request

```bash
# Access backend directly (http://localhost:8000/v1/messages)
# Or via frontend proxy (http://localhost:5173/v1/messages)
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-xxxxxxxxxxxxx" \
  -d '{
    "model": "haiku",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 100
  }'
```

### Streaming Request

```bash
# Access backend directly (http://localhost:8000/v1/messages)
# Or via frontend proxy (http://localhost:5173/v1/messages)
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-xxxxxxxxxxxxx" \
  -d '{
    "model": "sonnet",
    "messages": [{"role": "user", "content": "Tell me a story"}],
    "max_tokens": 200,
    "stream": true
  }'
```

### Tool Calling (Function Calling)

```bash
# Access backend directly (http://localhost:8000/v1/messages)
# Or via frontend proxy (http://localhost:5173/v1/messages)
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-xxxxxxxxxxxxx" \
  -d '{
    "model": "opus",
    "messages": [{"role": "user", "content": "What'"'"'s the weather in Beijing today?"}],
    "max_tokens": 200,
    "tools": [{
      "name": "get_weather",
      "description": "Get weather information for a specified city",
      "input_schema": {
        "type": "object",
        "properties": {
          "location": {
            "type": "string",
            "description": "City name"
          }
        },
        "required": ["location"]
      }
    }]
  }'
```

### Multimodal Input (Images)

```bash
# Access backend directly (http://localhost:8000/v1/messages)
# Or via frontend proxy (http://localhost:5173/v1/messages)
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-xxxxxxxxxxxxx" \
  -d '{
    "model": "sonnet",
    "messages": [{
      "role": "user",
      "content": [{
        "type": "text",
        "text": "What is this image about?"
      }, {
        "type": "image_url",
        "image_url": {
          "url": "https://example.com/image.jpg"
        }
      }]
    }],
    "max_tokens": 100
  }'
```

### System Prompt

```bash
# Access backend directly (http://localhost:8000/v1/messages)
# Or via frontend proxy (http://localhost:5173/v1/messages)
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-xxxxxxxxxxxxx" \
  -d '{
    "model": "sonnet",
    "system": "You are a helpful assistant that speaks in a friendly tone.",
    "messages": [
      {"role": "user", "content": "Hello"}
    ],
    "max_tokens": 100
  }'
```

### System Prompt with Tools

```bash
# Access backend directly (http://localhost:8000/v1/messages)
# Or via frontend proxy (http://localhost:5173/v1/messages)
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-xxxxxxxxxxxxx" \
  -d '{
    "model": "opus",
    "system": "You are a helpful assistant with access to tools.",
    "messages": [{"role": "user", "content": "Check the weather in Tokyo"}],
    "tools": [{
      "name": "get_weather",
      "description": "Get weather information",
      "input_schema": {
        "type": "object",
        "properties": {
          "location": {"type": "string"}
        }
      }
    }],
    "max_tokens": 200
  }'
```

### Using Different Models

```bash
# Use big model (opus/claude-3-opus)
# Access backend directly (http://localhost:8000/v1/messages)
# Or via frontend proxy (http://localhost:5173/v1/messages)
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-xxxxxxxxxxxxx" \
  -d '{
    "model": "opus",
    "messages": [{"role": "user", "content": "Explain quantum physics"}],
    "max_tokens": 500
  }'
```

### Custom Temperature and Top-P

```bash
# Access backend directly (http://localhost:8000/v1/messages)
# Or via frontend proxy (http://localhost:5173/v1/messages)
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-xxxxxxxxxxxxx" \
  -d '{
    "model": "sonnet",
    "messages": [{"role": "user", "content": "Write a creative story"}],
    "max_tokens": 300,
    "temperature": 0.8,
    "top_p": 0.9
  }'
```

### Response Metadata

```bash
# Access backend directly (http://localhost:8000/v1/messages)
# Or via frontend proxy (http://localhost:5173/v1/messages)
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-xxxxxxxxxxxxx" \
  -d '{
    "model": "haiku",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 50
  }'
```

Response will include:
- Model name
- Provider name
- Token usage (input/output)
- Processing time

## 📊 Status and Monitoring

### Real-time Health Monitoring

```bash
# Access backend directly (http://localhost:8000/health)
# Or via frontend proxy (http://localhost:5173/health)
curl http://localhost:8000/health

# Get detailed provider health information
curl -H "Authorization: Bearer <your-jwt-token>" \
  http://localhost:8000/api/health

# Trigger manual health check
curl -X POST -H "Authorization: Bearer <your-jwt-token>" \
  http://localhost:8000/api/health/check
```

### Performance Statistics

```bash
# Access backend directly (http://localhost:8000/api/stats/token-usage)
# Or via frontend proxy (http://localhost:5173/api/stats/token-usage)
curl -H "Authorization: Bearer <your-jwt-token>" \
  http://localhost:8000/api/stats/token-usage

# Get request statistics
curl -H "Authorization: Bearer <your-jwt-token>" \
  http://localhost:8000/api/stats/requests

# Get provider statistics
curl -H "Authorization: Bearer <your-jwt-token>" \
  http://localhost:8000/api/stats/providers
```

### Request Logs

```bash
# Access backend directly (http://localhost:8000/api/stats/requests)
# Or via frontend proxy (http://localhost:5173/api/stats/requests)
curl -H "Authorization: Bearer <your-jwt-token>" \
  http://localhost:8000/api/stats/requests

# Get detailed information about a specific request
curl -H "Authorization: Bearer <your-jwt-token>" \
  http://localhost:8000/api/stats/requests/{request_id}
```

## 🔧 Configuration

### Environment Variables Reference

#### Basic Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_SECRET_KEY` | Yes | - | Secret key for JWT token signing |
| `ENCRYPTION_KEY` | No | - | Fernet encryption key for sensitive data |
| `ADMIN_PASSWORD` | No | `admin123` | Admin user password |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

#### Performance Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_POOL_SIZE` | `10` | Database connection pool size |
| `DB_POOL_TIMEOUT` | `30.0` | Database connection pool timeout (seconds) |
| `HTTP_MAX_KEEPALIVE_CONNECTIONS` | `20` | Maximum keepalive connections |
| `HTTP_MAX_CONNECTIONS` | `100` | Maximum HTTP connections |
| `HTTP_KEEPALIVE_EXPIRY` | `5` | Keepalive connection expiry (seconds) |

#### Cache Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CACHE_TYPE` | `memory` | Cache type (memory, redis, multi) |
| `CACHE_MULTI_LEVEL` | `true` | Enable multi-level cache |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `CACHE_MAX_SIZE` | `100` | Maximum cache size |
| `CACHE_DEFAULT_TTL` | `3600` | Default cache TTL (seconds) |

#### Provider Configuration

| Variable | Description |
|----------|-------------|
| `QWEN_API_KEY` | Qwen provider API key |
| `MODELSCOPE_API_KEY` | ModelScope provider API key |
| `AIPING_API_KEY` | AI Ping provider API key |
| `MOONSHOT_API_KEY` | Moonshot provider API key |
| `ANTHROPIC_API_KEY` | Anthropic provider API key |

#### Monitoring Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_TELEMETRY` | `true` | Enable OpenTelemetry tracing |
| `OTLP_ENDPOINT` | - | OpenTelemetry collector endpoint |
| `SERVICE_VERSION` | `1.0.0` | Service version for tracing |
| `SAMPLING_RATE` | `0.1` | Request sampling rate (0.0-1.0) |

### Provider Configuration

#### Provider Object Structure

```json
{
  "name": "provider-name",
  "enabled": true,
  "priority": 1,
  "api_key": "sk-xxx",
  "base_url": "https://api.example.com/v1",
  "api_format": "openai",
  "timeout": 60,
  "max_retries": 1,
  "custom_headers": {},
  "models": {
    "big": ["model-1", "model-2"],
    "middle": ["model-3"],
    "small": ["model-4", "model-5"]
  }
}
```

#### Provider Types

**Anthropic Direct**
- `api_format`: "anthropic"
- `base_url`: "https://api.anthropic.com"
- Native Anthropic format, no conversion needed

**OpenAI Compatible**
- `api_format`: "openai"
- `base_url`: Provider's API URL
- Convert Anthropic format to provider format

#### Model Categories

**big** - Complex reasoning tasks
- Examples: claude-3-opus, qwen-max, gpt-4

**middle** - Balanced performance
- Examples: claude-3-sonnet, qwen-plus, gpt-3.5-turbo

**small** - Fast, simple tasks
- Examples: claude-3-haiku, qwen-turbo, gpt-3.5-turbo-instruct

## 🧪 Testing

### Run Tests (Backend)

```bash
# Run all tests
cd backend
pytest

# Run tests with coverage
pytest --cov=app --cov-report=html

# Run tests in parallel
pytest -n auto

# Run specific test file
pytest tests/test_messages.py -v

# Run test with markers
pytest -m "not slow"

# Run performance tests
pytest tests/test_performance.py
```

### Test Structure

```
tests/
├── test_messages.py          # Message API tests
├── test_converter.py         # Format conversion tests
├── test_streaming_format.py  # Streaming response tests
├── test_assistant_tool_use.py
├── test_tool_use_format.py
├── test_performance.py       # Performance tests
└── conftest.py              # Test configuration
```

### Load Testing

```bash
# Run load test (10k QPS)
cd backend
python tests/test_performance.py --qps 10000 --duration 60

# Test a specific provider
python tests/test_performance.py --provider qwen --qps 1000

# Test streaming performance
python tests/test_performance.py --streaming --qps 500
```

### Frontend Testing

```bash
# Type checking
cd frontend
pnpm run check

# Lint code
pnpm run lint

# Fix linting issues
pnpm run lint -- --write

# Build test
pnpm run build

# Preview build
pnpm run preview
```

## 🚀 Performance

### Benchmarks

**Throughput**: 10,000 requests/second on a single instance
**Latency**: < 100ms for simple requests (cache hit)
**Memory Usage**: ~500MB for typical workload
**CPU Usage**: 50% at 1,000 QPS

### Performance Tips

1. **Use Connection Pooling**
   - Enable HTTP keepalive connections
   - Increase pool size for high concurrency

2. **Enable Caching**
   - Use multi-level cache (memory + Redis)
   - Cache successful responses
   - Configure appropriate TTL

3. **Optimize Models**
   - Use appropriate model for task complexity
   - big model for reasoning, small for simple tasks

4. **Monitor Performance**
   - Enable OpenTelemetry tracking
   - Monitor request latency
   - Track token usage

### Circuit Breaker

The system includes a circuit breaker pattern:

```json
"circuit_breaker": {
  "failure_threshold": 5,
  "recovery_timeout": 60,
  "half_open_max_calls": 3
}
```

- **failure_threshold**: Number of failures to open circuit
- **recovery_timeout**: Seconds to wait before trying again
- **half_open_max_calls**: Number of test calls in half-open state

## 🐛 Troubleshooting

### Common Issues

#### Backend Won't Start

**Port Already in Use**
```bash
# Check what's using the port
lsof -i :8000

# Kill process
kill -9 <PID>
```

**Database Error**
```bash
# Check database permissions
ls -la backend/data/

# Recreate database
rm backend/data/app.db
# Restart backend
```

**Environment Variable Missing**
```bash
# Check required environment variables
echo $JWT_SECRET_KEY

# Set temporary key for testing
export JWT_SECRET_KEY="temp-secret-key-for-dev"
```

#### Frontend Won't Start

**Node Version Issue**
```bash
# Check Node version
node --version
# Should be 18+

# Install correct version
nvm install 20
nvm use 20
```

**Dependencies Issue**
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
pnpm install
```

**TypeScript Errors**
```bash
# Check TypeScript errors
pnpm run check

# Fix errors or disable check temporarily
pnpm run build --mode development
```

#### Provider Connection Issues

**Invalid API Key**
```bash
# Test API key with provider
curl -H "Authorization: Bearer $API_KEY" $BASE_URL/models
```

**Timeout**
```bash
# Test connection timeout
curl -v --max-time 10 $BASE_URL/models

# Increase timeout in provider.json
{
  "timeout": 300,
  "max_retries": 3
}
```

**Provider Unavailable**
```bash
# Check provider status
curl -H "Authorization: Bearer $API_KEY" $BASE_URL/models

# Disable problematic provider
{
  "name": "problematic-provider",
  "enabled": false
}
```

#### Database Issues

**Database Locked**
```bash
# Close all connections
ps aux | grep uvicorn
kill <PID>

# Or restart backend
```

**Migration Error**
```bash
# Backup and reset database
cp backend/data/app.db backend/data/app.db.backup
rm backend/data/app.db
# Restart backend to recreate schema
```

### Debug Mode

#### Backend Debug

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python -m uvicorn app.main:app --reload --log-level debug
```

#### Frontend Debug

```javascript
// Enable debug in browser console
localStorage.setItem('debug', 'http:*');

// View stores
import { get } from 'svelte/store';
import { authService } from '$services/auth';
console.log(get(authService));
```

### Log Analysis

#### Backend Logs

```bash
# View real-time logs
docker-compose logs -f backend

# Or with journalctl (if using systemd)
journalctl -u cc-switch -f

# Search for errors
grep "ERROR" backend/logs/app.log
```

#### Query Logs

```bash
# View recent requests
sqlite3 backend/data/app.db "SELECT * FROM request_logs ORDER BY created_at DESC LIMIT 10;"
```

---

<div align="center">

**Made with ❤️ by the CCS Team**

[Back to Main README](README.md) |
[Issue Tracker](https://github.com/michaelhuang7119/cc-switch/issues)

</div>