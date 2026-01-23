"""Database core functionality - connection and initialization."""
import os
import asyncio
import aiosqlite
import logging
from typing import Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class DatabaseCore:
    """Core database functionality for connection and schema initialization with connection pooling."""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database core.

        Args:
            db_path: Path to database file. If None, uses environment variable or default.
        """
        if db_path is None:
            db_path = os.getenv("DATABASE_PATH", str(Path(__file__).parent.parent.parent / "data" / "app.db"))

        # Ensure directory exists
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        self.db_path = db_path
        self._connections: List[aiosqlite.Connection] = []
        self._max_connections = int(os.getenv("DB_POOL_SIZE", "10"))
        self._pool_timeout = float(os.getenv("DB_POOL_TIMEOUT", "30.0"))
        self._lock = asyncio.Lock()

    async def get_connection(self) -> aiosqlite.Connection:
        """Get database connection from pool."""
        async with self._lock:
            # Try to reuse an existing connection
            while self._connections:
                conn = self._connections.pop()
                try:
                    # Check if connection is still valid
                    await conn.execute("SELECT 1")
                    return conn
                except Exception:
                    # Connection is invalid, close it and try another
                    try:
                        await conn.close()
                    except Exception:
                        pass
                    continue

        # Create new connection
        conn = await aiosqlite.connect(
            self.db_path,
            timeout=self._pool_timeout,
            check_same_thread=False
        )
        # Enable row factory for column access by name
        conn.row_factory = aiosqlite.Row
        # Set WAL mode for better concurrency
        cursor = await conn.cursor()
        await cursor.execute("PRAGMA journal_mode=WAL")
        await cursor.execute("PRAGMA synchronous=NORMAL")
        await cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
        await cursor.execute("PRAGMA temp_store=MEMORY")
        await conn.commit()
        await cursor.close()
        logger.debug(f"Created new database connection (pool size: {len(self._connections)}/{self._max_connections})")
        return conn

    async def release_connection(self, conn: aiosqlite.Connection):
        """Release connection back to pool."""
        async with self._lock:
            if len(self._connections) < self._max_connections:
                try:
                    await conn.execute("SELECT 1")  # Check connection is still valid
                    self._connections.append(conn)
                    return
                except Exception:
                    pass
            try:
                await conn.close()
            except Exception:
                pass

    async def close(self):
        """Close all database connections in pool."""
        async with self._lock:
            while self._connections:
                conn = self._connections.pop()
                try:
                    await conn.close()
                except Exception:
                    pass
            logger.info(f"Database connection pool closed ({len(self._connections)} connections)")

    async def init_database(self):
        """Initialize database schema."""
        conn = await self.get_connection()
        cursor = await conn.cursor()

        # Create request_logs table
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS request_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT NOT NULL,
                provider_name TEXT NOT NULL,
                model TEXT NOT NULL,
                request_params TEXT,
                response_data TEXT,
                status_code INTEGER,
                error_message TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                response_time_ms REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes
        await cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_request_logs_created_at
            ON request_logs(created_at)
        """)

        await cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_request_logs_provider_model
            ON request_logs(provider_name, model)
        """)

        await cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_request_logs_request_id
            ON request_logs(request_id)
        """)

        # Create provider_health_history table
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS provider_health_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_name TEXT NOT NULL,
                status TEXT NOT NULL,
                response_time_ms REAL,
                error_message TEXT,
                checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_health_history_provider
            ON provider_health_history(provider_name)
        """)

        await cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_health_history_checked_at
            ON provider_health_history(checked_at)
        """)

        # Create config_changes table for version control
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS config_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                change_type TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_name TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                changed_by TEXT,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_config_changes_entity
            ON config_changes(entity_type, entity_name)
        """)

        # Create token_usage table for cost tracking
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS token_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                provider_name TEXT NOT NULL,
                model TEXT NOT NULL,
                request_count INTEGER DEFAULT 0,
                total_input_tokens INTEGER DEFAULT 0,
                total_output_tokens INTEGER DEFAULT 0,
                total_cost_estimate REAL DEFAULT 0.0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, provider_name, model)
            )
        """)

        await cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_token_usage_date
            ON token_usage(date)
        """)

        # Create users table for admin authentication
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                name TEXT,
                language TEXT DEFAULT 'en-US',
                is_admin BOOLEAN DEFAULT 1,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login_at TIMESTAMP
            )
        """)

        await cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_email
            ON users(email)
        """)

        # 检查并添加 language 字段（如果不存在）
        await cursor.execute("PRAGMA table_info(users)")
        columns = [row['name'] for row in await cursor.fetchall()]
        if 'language' not in columns:
            await cursor.execute("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'en-US'")
            logger.info("Added language column to users table")

        # 检查并添加 permissions 字段（如果不存在）
        if 'permissions' not in columns:
            await cursor.execute("ALTER TABLE users ADD COLUMN permissions TEXT DEFAULT '{}'")
            logger.info("Added permissions column to users table")

        # Create api_keys table for API key management
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_hash TEXT NOT NULL UNIQUE,
                key_prefix TEXT NOT NULL,
                encrypted_key TEXT,
                name TEXT NOT NULL,
                email TEXT,
                user_id INTEGER,
                is_active BOOLEAN DEFAULT 1,
                last_used_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )
        """)

        # 检查并添加 encrypted_key 字段（如果不存在）
        await cursor.execute("PRAGMA table_info(api_keys)")
        columns = [row['name'] for row in await cursor.fetchall()]
        if 'encrypted_key' not in columns:
            await cursor.execute("ALTER TABLE api_keys ADD COLUMN encrypted_key TEXT")
            logger.info("Added encrypted_key column to api_keys table")

        await cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash
            ON api_keys(key_hash)
        """)

        await cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_keys_user_id
            ON api_keys(user_id)
        """)

        # Create conversations table for chat history
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                provider_name TEXT,
                api_format TEXT,
                model TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        await cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_user_id
            ON conversations(user_id)
        """)

        await cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_updated_at
            ON conversations(updated_at DESC)
        """)

        # Create conversation_messages table for storing chat messages
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                provider_name TEXT,
                model TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)

        # Add provider_name column if it doesn't exist (migration)
        await cursor.execute("PRAGMA table_info(conversation_messages)")
        columns = [row['name'] for row in await cursor.fetchall()]
        if 'provider_name' not in columns:
            await cursor.execute("ALTER TABLE conversation_messages ADD COLUMN provider_name TEXT")
            logger.info("Added provider_name column to conversation_messages table")

        # Add thinking column if it doesn't exist (migration)
        if 'thinking' not in columns:
            await cursor.execute("ALTER TABLE conversation_messages ADD COLUMN thinking TEXT")
            logger.info("Added thinking column to conversation_messages table")

        # Add api_format column if it doesn't exist (migration)
        if 'api_format' not in columns:
            await cursor.execute("ALTER TABLE conversation_messages ADD COLUMN api_format TEXT")
            logger.info("Added api_format column to conversation_messages table")

        # Add parent_message_id column if it doesn't exist (migration)
        if 'parent_message_id' not in columns:
            await cursor.execute("ALTER TABLE conversation_messages ADD COLUMN parent_message_id INTEGER")
            logger.info("Added parent_message_id column to conversation_messages table")

        # Add model_instance_index column if it doesn't exist (migration)
        if 'model_instance_index' not in columns:
            await cursor.execute("ALTER TABLE conversation_messages ADD COLUMN model_instance_index INTEGER DEFAULT 0")
            logger.info("Added model_instance_index column to conversation_messages table")

        await cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
            ON conversation_messages(conversation_id)
        """)

        await cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_created_at
            ON conversation_messages(created_at)
        """)

        # Create oauth_accounts table for OAuth2 authentication
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS oauth_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                provider TEXT NOT NULL,
                provider_user_id TEXT NOT NULL,
                access_token TEXT,
                refresh_token TEXT,
                token_expires_at TIMESTAMP,
                raw_user_info TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(provider, provider_user_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        await cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_oauth_accounts_user_id
            ON oauth_accounts(user_id)
        """)

        await cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_oauth_accounts_provider
            ON oauth_accounts(provider)
        """)

        await conn.commit()

        logger.info(f"Database initialized at {self.db_path}")

