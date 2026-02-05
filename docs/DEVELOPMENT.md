# Development Guide

This is the detailed development guide for **CC Switch**, aimed at developers who want to participate in project development, maintenance, or extension.

## Table of Contents

- [Project Architecture](#project-architecture)
- [Development Environment Setup](#development-environment-setup)
- [Code Standards](#code-standards)
- [Project Structure](#project-structure)
- [Core Flows](#core-flows)
- [Debugging Guide](#debugging-guide)
- [Adding New Features](#adding-new-features)
- [Database Management](#database-management)
- [Testing](#testing)
- [Deployment Guide](#deployment-guide)
- [API Documentation](#api-documentation)
- [Troubleshooting](#troubleshooting)
- [Contributing Guidelines](#contributing-guidelines)

---

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

## 🔧 Development Environment Setup

### Environment Setup

**1. Clone the Project**

```bash
git clone https://github.com/MichaelHuang7119/cc-switch.git
cd cc-switch
```

**2. Backend Development Environment**

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or venv\Scripts\activate  # Windows

# Install dependencies
pip install -e .

# Set environment variables
cp .env.example .env
# Edit .env file, configure necessary environment variables
```

**3. Frontend Development Environment**

```bash
cd frontend

# Install pnpm (if not installed)
npm install -g pnpm

# Install dependencies
pnpm install

# Start development server
pnpm dev
```

### Code Standards

**Backend (Python)**
- Use `black` for code formatting
- Use `isort` for import sorting
- Use `pylint` for static analysis
- Use `pytest` for unit testing

```bash
# Format code
black .
isort .

# Run tests
pytest

# Run tests (parallel)
pytest -n auto

# Code coverage
pytest --cov=app --cov-report=html
```

**Frontend (TypeScript/Svelte)**
- Use `eslint` for code linting
- Use `prettier` for code formatting
- Use `svelte-check` for type checking
- Follow Svelte 5 latest syntax specifications

```bash
# Type check
pnpm run check

# Lint code
pnpm run lint

# Fix code style
pnpm run lint -- --write

# Build production version
pnpm run build

# Preview build results
pnpm run preview
```

### Project Structure Explanation

**Request Flow**

```
Client Request
  ↓
API Routes (/routes/messages.py, /routes/*.py)
  ↓
Message Service (message_service.py)
  ↓
Converters (converters/)
  ↓
Provider Handler (services/handlers/)
  ↓
Provider Client (infrastructure/clients/)
  ↓
Backend AI Provider (OpenAI/Anthropic format)
  ↓
Response Conversion
  ↓
Client
```

**Backend Core Flow**

```
User Request
  │
  ▼
┌──────────────────┐
│   API Routes     │  ← Validate request parameters, JWT auth
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│    Services      │  ← Business logic processing
│  - Message Service│
│  - Provider Service│
│  - Health Service │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│    Converters    │  ← Anthropic ↔ OpenAI format conversion
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│   Provider API   │  ← Actually call backend AI services
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  Response Conv.  │  ← Convert response format
└──────┬───────────┘
       │
       ▼
    Return to User
```

**Frontend State Flow**

```
User Action
  │
  ▼
┌──────────────────┐
│   Svelte Components│  ← Trigger events
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│    Stores        │  ← State management
│  - writable      │
│  - derived       │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│   Services       │  ← API calls
│  - api.ts        │
│  - auth.ts       │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  Backend API     │  ← Data persistence
└──────────────────┘
```

## 🔍 Debugging Guide

### Backend Debugging

1. **Enable Debug Logging**
```bash
export LOG_LEVEL=DEBUG
```

2. **Use PyCharm/VSCode Debugging**
```bash
# Set breakpoints in VSCode, then:
python -m debugpy --listen 5678 --wait-for-child -m uvicorn app.main:app --reload
```

3. **Database Debugging**
```bash
# View database contents
sqlite3 backend/data/app.db
.tables
SELECT * FROM users;
```

### Frontend Debugging

1. **Browser Developer Tools**
```javascript
// View stores in console
import { get } from 'svelte/store';
import { authService } from '$services/auth';
console.log(get(authService));
```

2. **Svelte DevTools**
```bash
# Install browser extension
# https://github.com/sveltejs/svelte-devtools
```

3. **Network Request Debugging**
```bash
# Enable detailed logging
localStorage.setItem('debug', 'http');
```

## ➕ Adding New Features

### 1. Add New API Endpoint

Create file: `backend/app/api/example.py`

```python
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/example", tags=["example"])

@router.get("/")
async def get_example():
    return {"message": "Hello"}
```

Register in `main.py`:
```python
from .api.example import router as example_router
app.include_router(example_router)
```

### 2. Add New Frontend Page

Create file: `frontend/src/routes/example/+page.svelte`

```svelte
<script lang="ts">
  let message = "Hello";
</script>

<h1>{message}</h1>
```

### 3. Add New Database Table

In `backend/app/database/core.py` `init_database()` method, add:

```python
await cursor.execute("""
    CREATE TABLE IF NOT EXISTS example (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
```

## 💾 Database Management

### Database Schema

The project uses SQLite database with the following main tables:

- **users** - User accounts and preferences
- **api_keys** - API key management
- **conversations** - Chat conversation records
- **conversation_messages** - Individual messages
- **request_logs** - API request logs
- **token_usage** - Token usage statistics
- **provider_health_history** - Provider health records
- **config_changes** - Configuration change history

### Database Operations

**Initialize Database**
```bash
# Database is automatically initialized when backend starts
# Or manually:
python -c "from app.database.core import DatabaseCore; db = DatabaseCore(); import asyncio; asyncio.run(db.init_database())"
```

**Backup Database**
```bash
cp backend/data/app.db backend/data/app.db.backup
```

**Reset Database**
```bash
rm backend/data/app.db
# Restart backend to recreate
```

## 🧪 Testing

### Backend Testing

**Run All Tests**
```bash
cd backend
pytest

# With coverage
pytest --cov=app --cov-report=html

# Parallel execution
pytest -n auto

# Specific test file
pytest tests/test_messages.py -v
```

**Test Structure**
```
tests/
├── test_messages.py       # Message API tests
├── test_converter.py      # Format conversion tests
├── test_streaming_format.py
├── test_assistant_tool_use.py
├── test_tool_use_format.py
├── test_performance.py    # Performance tests
└── conftest.py           # Test configuration
```

### Frontend Testing

**Run Type Check**
```bash
cd frontend
pnpm run check
```

**Lint Code**
```bash
pnpm run lint
```

**Build Test**
```bash
pnpm run build
```

## 📦 Deployment

### Docker Deployment (Recommended)

**Production Environment**

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f
```

**Custom Configuration**

Create `.env.prod` file:

```bash
# Production configuration
JWT_SECRET_KEY=your-production-secret-key
ENCRYPTION_KEY=your-encryption-key
ADMIN_PASSWORD=your-secure-password

# Database configuration
DATABASE_PATH=/data/app.db

# Performance configuration
DB_POOL_SIZE=50
HTTP_MAX_CONNECTIONS=1000

# Logging configuration
LOG_LEVEL=INFO
```

Then start:

```bash
docker-compose --env-file .env.prod up -d
```

### Kubernetes Deployment

```bash
# Deploy to K8s
kubectl apply -f k8s/
```

### Manual Deployment

**1. Backend Deployment**

```bash
cd backend
source venv/bin/activate

# Production installation
pip install -e . --prod

# Use gunicorn to start
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

**2. Frontend Deployment**

```bash
cd frontend
pnpm install
pnpm build

# Deploy build/ directory to Nginx
cp -r build/* /var/www/html/
```

## 📖 API Documentation

### Core Endpoints

**Messages API**
- `POST /v1/messages` - Send message (Anthropic compatible)
- `POST /v1/messages/stream` - Stream response

**Provider Management**
- `GET /api/providers` - List providers
- `POST /api/providers` - Create provider
- `PUT /api/providers/{id}` - Update provider
- `DELETE /api/providers/{id}` - Delete provider

**Health Checks**
- `GET /health` - Basic health
- `GET /api/health` - Detailed health
- `POST /api/health/check` - Manual check

**Statistics**
- `GET /api/stats/token-usage` - Token usage
- `GET /api/stats/requests` - Request stats
- `GET /api/stats/providers` - Provider stats

**Conversations**
- `GET /api/conversations` - List conversations
- `POST /api/conversations` - Create conversation
- `GET /api/conversations/{id}` - Get conversation
- `DELETE /api/conversations/{id}` - Delete conversation

### Interactive API Docs

After starting the backend, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### API Examples

**Basic Request**
```bash
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-xxxxxxxxxxxxx" \
  -d '{"model": "haiku", "messages": [{"role": "user", "content": "Hello"}]}'
```

**With Streaming**
```bash
curl -X POST http://localhost:8000/v1/messages/stream \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-xxxxxxxxxxxxx" \
  -d '{"model": "sonnet", "messages": [{"role": "user", "content": "Hello"}], "stream": true}'
```

## ⚠️ Troubleshooting

### Common Issues

**1. Backend Won't Start**
```bash
# Check if port is already in use
lsof -i :8000

# Check environment variables
echo $JWT_SECRET_KEY

# Check database permissions
ls -la backend/data/
```

**2. Frontend Build Errors**
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
pnpm install

# Clear SvelteKit cache
rm -rf .svelte-kit

# Check TypeScript errors
pnpm run check
```

**3. Database Errors**
```bash
# Check database integrity
sqlite3 backend/data/app.db "PRAGMA integrity_check;"

# View table structure
sqlite3 backend/data/app.db ".schema users"
```

**4. Provider Connection Issues**
```bash
# Test provider connectivity
curl -H "Authorization: Bearer $API_KEY" $PROVIDER_BASE_URL/models

# Check provider configuration
cat backend/provider.json | jq '.providers[] | select(.enabled == true)'
```

### Debug Mode

**Backend Debug Mode**
```bash
export LOG_LEVEL=DEBUG
cd backend && python -m uvicorn app.main:app --reload --log-level debug
```

**Frontend Debug Mode**
```bash
# Enable debug in browser console
localStorage.setItem('debug', 'http:*');
```

## 🤝 Contributing Guidelines

We welcome all forms of contribution!

### How to Contribute

1. **Fork** the repository
2. Create feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -am 'Add some feature'`
4. Push branch: `git push origin feature/your-feature`
5. Submit **Pull Request**

### Contribution Standards

**Code Style**
- Backend: Follow PEP 8
- Frontend: Follow project ESLint configuration
- Commit messages: Use conventional commit format

```bash
# Example commit messages
feat(api): add new endpoint for statistics
fix(frontend): resolve chat timestamp issue
docs(readme): update deployment guide
```

**Commit Types**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation update
- `style`: Code formatting
- `refactor`: Refactoring
- `test`: Testing
- `chore`: Build process or auxiliary tools

### Pull Request Requirements

- [ ] Code passes all tests
- [ ] Passes ESLint/Prettier checks
- [ ] Added necessary unit tests
- [ ] Updated relevant documentation
- [ ] PR description written in English

### Reporting Issues

Please use [GitHub Issues](https://github.com/michaelhuang7119/cc-switch/issues) to report issues.

**Bug Report Template**:

```markdown
## 🐛 Bug Description
Clear and concise description of the bug.

## 🔄 Reproduction Steps
1. Go to...
2. Click on...
3. Scroll to...
4. See error

## ✅ Expected Behavior
Clear and concise description of what you expected to happen.

## 📸 Screenshots
If applicable, add screenshots.

## 🖥️ Environment Information
- OS: [e.g. Ubuntu 20.04]
- Browser: [e.g. Chrome 91]
- Python: [e.g. 3.11.0]
- Node.js: [e.g. 18.0.0]
```

### Feature Requests

```markdown
## 🚀 Feature Description
Clear and concise description of the feature you want.

## 💡 Detailed Description
Detailed description of the feature's implementation plan.

## 🎯 Use Case
Describe the use case for this feature.
```

---

## 📚 Additional Resources

- **API Documentation**: http://localhost:8000/docs
- **Project Website**: (Coming Soon)
- **Community Forum**: (Coming Soon)
- **Video Tutorials**: (Coming Soon)

---

<div align="center">

**Made with ❤️ by the CCS Team**

[Back to Main README](README.md) |
[Issue Tracker](https://github.com/michaelhuang7119/cc-switch/issues)

</div>
